"""
Сигналы: новая запись в EKM → push в МИС клиники.

Чтобы не блокировать пользователя на сетевом запросе — push выполняется
в потоке (минимальный без-Celery вариант). На проде стоит вынести в
очередь (Celery / RQ).
"""
from __future__ import annotations

import logging
import threading

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from appointments.models import Appointment

from .models import ClinicIntegration, IntegrationEvent

log = logging.getLogger(__name__)


@receiver(post_save, sender=Appointment)
def push_appointment_to_mis(sender, instance: Appointment, created: bool, **kwargs):
    if not created:
        return
    if not instance.clinic_id:
        return

    integration = getattr(instance.clinic, 'integration', None)
    if not integration or not integration.is_active or not integration.push_appointments:
        return

    def _do_push(appt_pk: int, integration_pk: int):
        # Импорт внутри, чтобы избежать циркулярных импортов при загрузке app
        from .adapters import get_adapter, AdapterError
        try:
            integ = ClinicIntegration.objects.select_related('clinic').get(pk=integration_pk)
            appt  = Appointment.objects.select_related('vet', 'pet', 'owner').get(pk=appt_pk)
            adapter = get_adapter(integ)
            adapter.push_appointment(appt)
            integ.last_sync_at = timezone.now()
            integ.last_error = ''
            integ.save(update_fields=['last_sync_at', 'last_error'])
        except AdapterError as e:
            log.warning('MIS push failed for appointment=%s: %s', appt_pk, e)
            try:
                integ = ClinicIntegration.objects.get(pk=integration_pk)
                integ.last_error = str(e)[:1000]
                integ.save(update_fields=['last_error'])
                IntegrationEvent.objects.create(
                    integration=integ, direction='out', kind='appointment_push',
                    status='error', error=str(e),
                    payload={'appointment_id': appt_pk},
                )
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            log.exception('Unexpected error in MIS push')

    # daemon-поток: процесс runserver не повиснет на закрытии
    t = threading.Thread(
        target=_do_push, args=(instance.pk, integration.pk), daemon=True,
    )
    t.start()
