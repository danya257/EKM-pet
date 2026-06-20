"""
python manage.py mis_pull_visits [--days 7]

Для всех заявок последних N дней со статусом 'confirmed' пытается забрать
итог визита из МИС. Если визит вернулся — закрываем заявку, сохраняем Visit.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.models import Appointment
from integrations.adapters import AdapterError, get_adapter
from integrations.services import apply_visit


class Command(BaseCommand):
    help = 'Pull completed visits from MIS for recent appointments.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)

    def handle(self, *args, **opts):
        since = timezone.now() - timedelta(days=opts['days'])
        appts = (
            Appointment.objects
            .filter(scheduled_at__gte=since,
                    status__in=[Appointment.STATUS_NEW, Appointment.STATUS_CONFIRMED])
            .select_related('clinic__integration', 'vet', 'pet')
        )
        for appt in appts:
            integ = getattr(appt.clinic, 'integration', None) if appt.clinic_id else None
            if not integ or not integ.is_active or not integ.pull_visits:
                continue
            try:
                adapter = get_adapter(integ)
                dto = adapter.pull_visit(appt)
            except AdapterError as e:
                self.stderr.write(f'! {appt}: {e}')
                continue
            if not dto:
                continue
            apply_visit(integ, dto, appointment=appt)
            self.stdout.write(self.style.SUCCESS(f'· {appt}: visit synced'))
