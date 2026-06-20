"""
python manage.py mis_pull_schedules [--days 14]

Тянет свободные слоты всех врачей всех активных интеграций на N дней вперёд.
Запускать кроном раз в N минут (15-60 — в зависимости от того, как часто
у клиники меняется расписание).
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from integrations.adapters import AdapterError, get_adapter
from integrations.models import ClinicIntegration
from integrations.services import replace_slots_window, upsert_slot


class Command(BaseCommand):
    help = 'Pull schedule slots from all active MIS integrations.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=14)
        parser.add_argument('--integration', type=int, help='Только эта интеграция (id)')

    def handle(self, *args, **opts):
        qs = ClinicIntegration.objects.filter(is_active=True, pull_schedule=True)
        if opts.get('integration'):
            qs = qs.filter(pk=opts['integration'])

        today = timezone.localdate()
        end = today + timedelta(days=opts['days'])

        for integ in qs.select_related('clinic'):
            self.stdout.write(self.style.NOTICE(f'\n[{integ}]'))
            try:
                adapter = get_adapter(integ)
            except AdapterError as e:
                self.stderr.write(f'  ! {e}')
                continue

            vets = list(integ.clinic.vets.filter(is_published=True))
            for vet in vets:
                try:
                    slots = list(adapter.pull_schedule(vet, today, end))
                except AdapterError as e:
                    self.stderr.write(f'  ! {vet}: {e}')
                    continue
                if not slots:
                    self.stdout.write(f'  · {vet}: 0 slots')
                    continue
                replace_slots_window(integ, vet, today, end)
                for s in slots:
                    upsert_slot(integ, vet, s)
                self.stdout.write(self.style.SUCCESS(f'  · {vet}: {len(slots)} slots'))

            integ.last_sync_at = timezone.now()
            integ.save(update_fields=['last_sync_at'])
