"""
Endpoints интеграционного слоя.

OUTBOUND (МИС читает у нас) — REST под OAuth2:
    GET  /integrations/api/appointments/    — новые заявки клиники
    GET  /integrations/api/appointments/<id>/
    GET  /integrations/api/services/         — наши услуги
    POST /integrations/api/visits/           — МИС шлёт итог визита
    POST /integrations/api/services/sync/    — МИС шлёт прайс (массово)

INBOUND (МИС → нам, generic webhook):
    POST /integrations/webhook/<integration_id>/   с HMAC-подписью
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from django.http import HttpRequest, HttpResponseForbidden, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from oauth2_provider.decorators import protected_resource

from appointments.models import Appointment
from clinics.models import Clinic
from services.models import Service

from .adapters.base import VisitDTO
from .models import ClinicIntegration, IntegrationEvent
from .services import apply_visit


# =========================================================================
#  Helpers
# =========================================================================

def _clinic_for_token(request: HttpRequest) -> Clinic | None:
    """Из OAuth-токена достаём клинику. Привязка: токен.application.user →
    User, у которого есть managed_clinics. Берём первую."""
    tok = getattr(request, 'access_token', None)
    if tok is None or tok.application is None:
        return None
    owner = tok.application.user
    if owner is None:
        return None
    return owner.managed_clinics.first()


def _appt_to_json(a: Appointment) -> dict:
    return {
        'id':           a.pk,
        'status':       a.status,
        'scheduled_at': a.scheduled_at.isoformat(),
        'kind':         a.kind,
        'reason':       a.reason,
        'contact_phone': a.contact_phone,
        'vet':   {'id': a.vet_id,    'name': str(a.vet) if a.vet else None},
        'pet':   {'id': a.pet_id,    'name': a.pet.name if a.pet else None,
                  'species': a.pet.species if a.pet else None,
                  'chip':    a.pet.chip_number if a.pet else None},
        'owner': {'id': a.owner_id,
                  'name': a.owner.get_full_name() or a.owner.username,
                  'email': a.owner.email,
                  'phone': a.contact_phone},
        'service': {'id': a.service_id, 'name': a.service.name if a.service else None,
                    'price': float(a.service.price) if a.service else None},
    }


# =========================================================================
#  OUTBOUND REST API — OAuth-защищённый
# =========================================================================

@require_GET
@protected_resource(scopes=['mis:read'])
def api_appointments_list(request: HttpRequest):
    clinic = _clinic_for_token(request)
    if not clinic:
        return JsonResponse({'detail': 'OAuth-приложение не привязано к клинике'}, status=403)

    qs = Appointment.objects.filter(clinic=clinic).order_by('-created_at')

    since = request.GET.get('since')
    if since:
        try:
            dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            qs = qs.filter(updated_at__gte=dt)
        except ValueError:
            return JsonResponse({'detail': 'since: неверный формат (ISO-8601)'}, status=400)

    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)

    limit = min(int(request.GET.get('limit', 100) or 100), 500)
    items = [_appt_to_json(a) for a in qs[:limit]]
    return JsonResponse({'count': len(items), 'results': items})


@require_GET
@protected_resource(scopes=['mis:read'])
def api_appointment_detail(request: HttpRequest, pk: int):
    clinic = _clinic_for_token(request)
    if not clinic:
        return JsonResponse({'detail': 'OAuth-приложение не привязано к клинике'}, status=403)
    a = get_object_or_404(Appointment, pk=pk, clinic=clinic)
    return JsonResponse(_appt_to_json(a))


@require_GET
@protected_resource(scopes=['mis:read'])
def api_services_list(request: HttpRequest):
    clinic = _clinic_for_token(request)
    if not clinic:
        return JsonResponse({'detail': 'OAuth-приложение не привязано к клинике'}, status=403)
    items = [
        {'id': s.pk, 'name': s.name, 'price': float(s.price),
         'description': s.description}
        for s in clinic.services.all().order_by('name')
    ]
    return JsonResponse({'count': len(items), 'results': items})


@csrf_exempt
@require_POST
@protected_resource(scopes=['mis:write'])
def api_visit_create(request: HttpRequest):
    """МИС шлёт итог визита.

    Body: {
        "appointment_id": 42,               // наш id заявки (опционально)
        "external_id":   "VM-9981",         // их id (для будущей сверки)
        "visited_at":    "2026-06-20T14:35:00+03:00",
        "diagnosis":     "...",
        "treatment":     "...",
        "services":     [{"name": "...", "price": 1500, "qty": 1, "sum": 1500}],
        "documents":    [{"url": "...", "title": "..."}]
    }
    """
    clinic = _clinic_for_token(request)
    if not clinic or not hasattr(clinic, 'integration'):
        return JsonResponse({'detail': 'Нет привязки клиники к интеграции'}, status=403)

    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Кривой JSON'}, status=400)

    integration = clinic.integration
    appt = None
    if body.get('appointment_id'):
        appt = Appointment.objects.filter(pk=body['appointment_id'], clinic=clinic).first()

    try:
        visited_at = datetime.fromisoformat(str(body.get('visited_at')).replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return JsonResponse({'detail': 'visited_at обязателен (ISO-8601)'}, status=400)

    services = body.get('services') or []
    total = sum(Decimal(str(s.get('sum') or s.get('price') or 0)) for s in services)

    dto = VisitDTO(
        visited_at=visited_at,
        diagnosis=body.get('diagnosis', ''),
        treatment=body.get('treatment', ''),
        services=services,
        total=total,
        documents=body.get('documents') or [],
        external_id=str(body.get('external_id') or ''),
        pet_ext_id=str(body.get('pet_ext_id') or ''),
        vet_ext_id=str(body.get('vet_ext_id') or ''),
        raw=body,
    )
    visit = apply_visit(integration, dto, appointment=appt)
    IntegrationEvent.objects.create(
        integration=integration, direction=IntegrationEvent.DIR_IN,
        kind='visit_in', payload=body, response={'visit_id': visit.pk},
    )
    return JsonResponse({'visit_id': visit.pk, 'appointment_id': appt.pk if appt else None})


@csrf_exempt
@require_POST
@protected_resource(scopes=['mis:write'])
def api_services_sync(request: HttpRequest):
    """МИС шлёт прайс целиком. Body: {"services": [{"name":..., "price":...}, ...]}"""
    clinic = _clinic_for_token(request)
    if not clinic:
        return JsonResponse({'detail': 'OAuth-приложение не привязано к клинике'}, status=403)

    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Кривой JSON'}, status=400)

    incoming = body.get('services') or []
    created, updated = 0, 0
    for row in incoming:
        name = (row.get('name') or '').strip()
        if not name:
            continue
        obj, was_created = Service.objects.update_or_create(
            clinic=clinic, name=name,
            defaults={
                'price':       Decimal(str(row.get('price') or 0)),
                'description': row.get('description') or '',
            },
        )
        if was_created: created += 1
        else:           updated += 1

    if hasattr(clinic, 'integration'):
        IntegrationEvent.objects.create(
            integration=clinic.integration, direction=IntegrationEvent.DIR_IN,
            kind='services_sync',
            payload={'count': len(incoming)},
            response={'created': created, 'updated': updated},
        )
    return JsonResponse({'created': created, 'updated': updated, 'total': created + updated})


# =========================================================================
#  INBOUND webhook (generic, HMAC-подпись вместо OAuth)
# =========================================================================

@csrf_exempt
@require_POST
def webhook_in(request: HttpRequest, integration_id: int):
    """Универсальный приёмник событий от МИС.

    Headers:
        X-EKM-Signature: sha256=<hex>      — HMAC от тела с webhook_secret

    Body: { "event": "visit.completed" | "schedule.updated" | ..., "data": {...} }
    """
    integration = get_object_or_404(ClinicIntegration, pk=integration_id, is_active=True)
    body = request.body or b''

    if not _verify_signature(request, body, integration.webhook_secret):
        return HttpResponseForbidden('Bad signature')

    try:
        payload = json.loads(body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Кривой JSON'}, status=400)

    event = payload.get('event') or 'unknown'
    data = payload.get('data') or {}

    IntegrationEvent.objects.create(
        integration=integration, direction=IntegrationEvent.DIR_IN,
        kind=event, payload=payload,
    )

    # Минимальная маршрутизация. Расширять по мере нужды.
    if event == 'visit.completed':
        try:
            visited_at = datetime.fromisoformat(str(data.get('visited_at')).replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return JsonResponse({'detail': 'visited_at обязателен'}, status=400)

        services = data.get('services') or []
        total = sum(Decimal(str(s.get('sum') or s.get('price') or 0)) for s in services)
        dto = VisitDTO(
            visited_at=visited_at,
            diagnosis=data.get('diagnosis', ''),
            treatment=data.get('treatment', ''),
            services=services,
            total=total,
            documents=data.get('documents') or [],
            external_id=str(data.get('external_id') or ''),
            pet_ext_id=str(data.get('pet_ext_id') or ''),
            vet_ext_id=str(data.get('vet_ext_id') or ''),
            raw=data,
        )
        visit = apply_visit(integration, dto)
        return JsonResponse({'ok': True, 'visit_id': visit.pk})

    # Для незнакомых событий — просто 200 (мы сохранили в IntegrationEvent).
    return JsonResponse({'ok': True, 'stored': True})


def _verify_signature(request: HttpRequest, body: bytes, secret: str) -> bool:
    header = request.headers.get('X-EKM-Signature', '')
    if not header.startswith('sha256='):
        return False
    expected = header.split('=', 1)[1].lower()
    actual = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, actual)
