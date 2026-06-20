"""
python manage.py mis_pull_services

Тянет прайс всех активных интеграций и приземляет в services.Service.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from integrations.adapters import AdapterError, get_adapter
from integrations.models import ClinicIntegration
from services.models import Service


class Command(BaseCommand):
    help = 'Pull services (price list) from all active MIS integrations.'

    def handle(self, *args, **opts):
        qs = ClinicIntegration.objects.filter(is_active=True, pull_services=True)
        for integ in qs.select_related('clinic'):
            self.stdout.write(self.style.NOTICE(f'\n[{integ}]'))
            try:
                adapter = get_adapter(integ)
                rows = list(adapter.sync_services())
            except AdapterError as e:
                self.stderr.write(f'  ! {e}')
                continue

            created, updated = 0, 0
            for s in rows:
                _obj, was_created = Service.objects.update_or_create(
                    clinic=integ.clinic, name=s.name,
                    defaults={'price': s.price or Decimal('0'),
                              'description': s.description},
                )
                if was_created: created += 1
                else:           updated += 1

            self.stdout.write(self.style.SUCCESS(
                f'  · sync: {created} new, {updated} updated, {len(rows)} total'))
            integ.last_sync_at = timezone.now()
            integ.save(update_fields=['last_sync_at'])
