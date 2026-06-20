"""
Сервисный слой — то, что вызывают и адаптеры (pull), и inbound webhook.

Идея: куда бы данные ни пришли — через GET-pull или через POST-webhook —
они проходят через одну функцию `apply_visit` / `apply_slot`, которая
обновляет домен и пишет в лог.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from appointments.models import Appointment
from clinics.models import VetProfile
from pets.models import Pet

from .adapters.base import SlotDTO, VisitDTO
from .models import (
    ClinicIntegration, ExternalMapping, ScheduleSlot, Visit,
)


# ---------------------------------------------------------------------------
#  Visit
# ---------------------------------------------------------------------------

@transaction.atomic
def apply_visit(integration: ClinicIntegration, dto: VisitDTO,
                appointment: Appointment | None = None) -> Visit:
    """Сохранить итог визита.

    Если appointment не передан — пытаемся найти по ExternalMapping
    (external_id из dto). Если и его нет — создаём «осиротевший» Visit,
    привязанный только к питомцу (если смогли распознать).
    """
    if appointment is None and dto.external_id:
        m = ExternalMapping.objects.filter(
            integration=integration,
            local_kind='appointments.appointment',
            external_id=dto.external_id,
        ).first()
        if m:
            appointment = Appointment.objects.filter(pk=m.local_id).first()

    pet = appointment.pet if appointment else _resolve_pet(integration, dto)
    vet = appointment.vet if appointment else _resolve_vet(integration, dto)

    defaults = {
        'integration':  integration,
        'pet':          pet,
        'vet':          vet,
        'visited_at':   dto.visited_at,
        'diagnosis':    dto.diagnosis,
        'treatment':    dto.treatment,
        'services_done': dto.services,
        'total':        dto.total or Decimal('0'),
        'documents':    dto.documents,
        'raw_payload':  dto.raw,
        'external_id':  dto.external_id,
    }

    if appointment is not None:
        visit, _ = Visit.objects.update_or_create(appointment=appointment, defaults=defaults)
        # Закрываем заявку, если она ещё открыта
        if appointment.status in (Appointment.STATUS_NEW, Appointment.STATUS_CONFIRMED):
            appointment.status = Appointment.STATUS_DONE
            appointment.save(update_fields=['status', 'updated_at'])
    else:
        # без appointment — ищем по external_id+integration или создаём
        if dto.external_id:
            visit, _ = Visit.objects.update_or_create(
                integration=integration, external_id=dto.external_id,
                defaults=defaults,
            )
        else:
            visit = Visit.objects.create(**defaults)
    return visit


def _resolve_pet(integration: ClinicIntegration, dto: VisitDTO) -> Optional[Pet]:
    if not dto.pet_ext_id:
        return None
    m = ExternalMapping.objects.filter(
        integration=integration,
        local_kind='pets.pet',
        external_id=dto.pet_ext_id,
    ).first()
    return Pet.objects.filter(pk=m.local_id).first() if m else None


def _resolve_vet(integration: ClinicIntegration, dto: VisitDTO) -> Optional[VetProfile]:
    if not dto.vet_ext_id:
        return None
    m = ExternalMapping.objects.filter(
        integration=integration,
        local_kind='clinics.vetprofile',
        external_id=dto.vet_ext_id,
    ).first()
    return VetProfile.objects.filter(pk=m.local_id).first() if m else None


# ---------------------------------------------------------------------------
#  Schedule slot
# ---------------------------------------------------------------------------

@transaction.atomic
def upsert_slot(integration: ClinicIntegration, vet: VetProfile, dto: SlotDTO) -> ScheduleSlot:
    key = {'integration': integration, 'external_id': dto.external_id} \
        if dto.external_id else {'vet': vet, 'starts_at': dto.starts_at}
    slot, _ = ScheduleSlot.objects.update_or_create(
        **key,
        defaults={
            'vet':          vet,
            'integration':  integration,
            'starts_at':    dto.starts_at,
            'duration_min': dto.duration_min,
            'is_available': dto.is_available,
            'external_id':  dto.external_id,
            'pulled_at':    timezone.now(),
        },
    )
    return slot


def replace_slots_window(integration: ClinicIntegration, vet: VetProfile, frm, to) -> None:
    """Удалить устаревшие слоты в окне перед перезаписью."""
    ScheduleSlot.objects.filter(
        integration=integration, vet=vet,
        starts_at__gte=frm, starts_at__lt=to,
    ).delete()
