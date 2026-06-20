"""
Адаптер «generic webhook + REST».

Идея: клиника не имеет полноценного API — мы предоставляем им наш REST
и одновременно дёргаем настраиваемый webhook когда у нас что-то происходит.

OUTBOUND (мы → клиника):
    POST  {webhook_url}                — событие, payload = JSON
                                          заголовок X-EKM-Signature: HMAC-SHA256

INBOUND (клиника → нам):
    POST /integrations/webhook/<int_id>/  — приходит сюда в views.webhook_in,
                                          не в адаптер.

В extra можно положить:
    "webhook_url": "https://crm.example.com/hook/ekm"
    "schedule_url": "https://crm.example.com/api/schedule"      # GET для pull
    "visit_url":    "https://crm.example.com/api/visit/{ext}"   # GET для pull
    "services_url": "https://crm.example.com/api/services"
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Optional

import requests
from django.utils import timezone

from .base import (
    AdapterError, MISAdapter, NotFound,
    PushResult, ServiceDTO, SlotDTO, VisitDTO,
)


class WebhookAdapter(MISAdapter):
    name = 'webhook'
    timeout = 10

    def _signed_headers(self, body_bytes: bytes) -> dict:
        secret = self.integration.webhook_secret.encode()
        sig = hmac.new(secret, body_bytes, hashlib.sha256).hexdigest()
        return {
            'Content-Type':    'application/json',
            'X-EKM-Signature': f'sha256={sig}',
            'X-EKM-Clinic':    str(self.clinic.pk),
        }

    def _post(self, url: str, payload: dict, log_kind: str) -> dict:
        body = json.dumps(payload, default=str, ensure_ascii=False).encode('utf-8')
        try:
            r = requests.post(url, data=body, headers=self._signed_headers(body),
                              timeout=self.timeout)
        except requests.RequestException as e:
            self._log(direction='out', kind=log_kind, payload=payload, error=str(e))
            raise AdapterError(f'Webhook network: {e}') from e

        try:
            data = r.json() if r.content else {}
        except ValueError:
            data = {'_raw': r.text}
        self._log(direction='out', kind=log_kind, http_code=r.status_code,
                  payload=payload, response=data,
                  error='' if r.ok else f'HTTP {r.status_code}')
        if not r.ok:
            raise AdapterError(f'Webhook {r.status_code}: {data}')
        return data if isinstance(data, dict) else {'data': data}

    def _get(self, url: str, params: dict | None, log_kind: str) -> dict:
        try:
            r = requests.get(url, params=params, headers=self._signed_headers(b''),
                             timeout=self.timeout)
        except requests.RequestException as e:
            self._log(direction='out', kind=log_kind, payload=params or {}, error=str(e))
            raise AdapterError(f'Webhook network: {e}') from e
        try:
            data = r.json() if r.content else {}
        except ValueError:
            data = {'_raw': r.text}
        self._log(direction='out', kind=log_kind, http_code=r.status_code,
                  payload=params or {}, response=data,
                  error='' if r.ok else f'HTTP {r.status_code}')
        if r.status_code == 404:
            raise NotFound(url)
        if not r.ok:
            raise AdapterError(f'Webhook {r.status_code}: {data}')
        return data if isinstance(data, dict) else {'data': data}

    # ---- интерфейс ------------------------------------------------------
    def health_check(self) -> bool:
        url = self.integration.extra.get('health_url')
        if not url:
            # без health-URL считаем интеграцию валидной, если есть secret
            return bool(self.integration.webhook_secret)
        try:
            self._get(url, None, 'health_check')
            return True
        except AdapterError:
            return False

    def push_appointment(self, appointment) -> PushResult:
        url = self.integration.extra.get('webhook_url')
        if not url:
            raise AdapterError('extra.webhook_url не задан')
        payload = {
            'event': 'appointment.created',
            'appointment': {
                'id':           appointment.pk,
                'scheduled_at': appointment.scheduled_at.isoformat(),
                'kind':         appointment.kind,
                'reason':       appointment.reason,
                'contact_phone': appointment.contact_phone,
                'vet_id':       appointment.vet_id,
                'pet':          {'id': appointment.pet_id,
                                 'name': getattr(appointment.pet, 'name', '') if appointment.pet else ''},
                'owner':        {'id': appointment.owner_id,
                                 'name': appointment.owner.get_full_name() or appointment.owner.username},
            },
        }
        data = self._post(url, payload, 'appointment_push')
        ext_id = str(data.get('external_id') or data.get('id') or '')
        if ext_id:
            self._save_mapping(local_kind='appointments.appointment',
                               local_id=appointment.pk, external_id=ext_id)
        return PushResult(external_id=ext_id, raw=data)

    def pull_schedule(self, vet, date_from: date, date_to: date) -> Iterable[SlotDTO]:
        url = self.integration.extra.get('schedule_url')
        if not url:
            return iter([])
        data = self._get(url, {'vet_id': vet.pk,
                               'from': date_from.isoformat(),
                               'to':   date_to.isoformat()}, 'schedule_pull')
        for row in data.get('slots') or []:
            yield SlotDTO(
                starts_at    = _parse_dt(row.get('start')),
                duration_min = int(row.get('duration_min') or 30),
                is_available = bool(row.get('available', True)),
                external_id  = str(row.get('id') or ''),
            )

    def pull_visit(self, appointment) -> Optional[VisitDTO]:
        url_tpl = self.integration.extra.get('visit_url')
        if not url_tpl:
            return None
        ext = self._get_external_id(local_kind='appointments.appointment', local_id=appointment.pk)
        if not ext:
            return None
        try:
            data = self._get(url_tpl.format(ext=ext, appointment_id=appointment.pk),
                             None, 'visit_pull')
        except NotFound:
            return None
        if not data.get('visited_at'):
            return None
        services = data.get('services') or []
        total = sum(Decimal(str(s.get('sum') or s.get('price') or 0)) for s in services)
        return VisitDTO(
            visited_at = _parse_dt(data.get('visited_at')),
            diagnosis  = data.get('diagnosis', ''),
            treatment  = data.get('treatment', ''),
            services   = services,
            total      = total,
            documents  = data.get('documents') or [],
            external_id = ext,
            raw         = data,
        )

    def sync_services(self) -> Iterable[ServiceDTO]:
        url = self.integration.extra.get('services_url')
        if not url:
            return iter([])
        data = self._get(url, None, 'services_pull')
        for row in data.get('services') or []:
            yield ServiceDTO(
                name=row.get('name') or '?',
                price=Decimal(str(row.get('price') or 0)),
                description=row.get('description', ''),
                external_id=str(row.get('id') or ''),
            )


def _parse_dt(value):
    if not value:
        return timezone.now()
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except ValueError:
            return timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt
