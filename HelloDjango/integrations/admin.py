from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from .adapters import AdapterError, get_adapter
from .models import (
    ClinicIntegration, ExternalMapping, IntegrationEvent,
    ScheduleSlot, Visit,
)


@admin.register(ClinicIntegration)
class ClinicIntegrationAdmin(admin.ModelAdmin):
    list_display = ('clinic', 'kind', 'is_active', 'last_sync_at', 'health_ok', 'last_error_short')
    list_filter = ('kind', 'is_active')
    search_fields = ('clinic__name',)
    autocomplete_fields = ('clinic',)
    readonly_fields = ('webhook_secret', 'last_sync_at', 'last_error', 'created_at', 'updated_at')
    actions = ['action_health_check', 'action_pull_services', 'action_pull_schedule']

    fieldsets = (
        (None, {'fields': ('clinic', 'kind', 'is_active')}),
        ('Подключение', {'fields': ('base_url', 'oauth_client_id', 'api_token', 'extra')}),
        ('Сценарии', {'fields': ('push_appointments', 'pull_schedule', 'pull_visits', 'pull_services')}),
        ('Webhook (inbound от МИС)', {'fields': ('webhook_secret',)}),
        ('Состояние', {'fields': ('last_sync_at', 'last_error', 'created_at', 'updated_at')}),
    )

    @admin.display(description='Health')
    def health_ok(self, obj):
        return '—'  # дешевле в списке не дёргать сеть

    @admin.display(description='Ошибка')
    def last_error_short(self, obj):
        return (obj.last_error or '')[:60]

    @admin.action(description='Health check (дёрнуть API)')
    def action_health_check(self, request, queryset):
        for integ in queryset:
            try:
                ok = get_adapter(integ).health_check()
                level = messages.SUCCESS if ok else messages.WARNING
                self.message_user(request, f'{integ}: {"OK" if ok else "FAIL"}', level=level)
            except AdapterError as e:
                self.message_user(request, f'{integ}: {e}', level=messages.ERROR)

    @admin.action(description='Синхронизировать прайс')
    def action_pull_services(self, request, queryset):
        from services.models import Service
        from decimal import Decimal
        for integ in queryset:
            try:
                rows = list(get_adapter(integ).sync_services())
                c = u = 0
                for s in rows:
                    _, was_created = Service.objects.update_or_create(
                        clinic=integ.clinic, name=s.name,
                        defaults={'price': s.price or Decimal('0'), 'description': s.description},
                    )
                    c += int(was_created); u += int(not was_created)
                self.message_user(request, f'{integ}: {c} нов, {u} обнов', level=messages.SUCCESS)
            except AdapterError as e:
                self.message_user(request, f'{integ}: {e}', level=messages.ERROR)

    @admin.action(description='Подтянуть расписание на 14 дней')
    def action_pull_schedule(self, request, queryset):
        from django.core.management import call_command
        for integ in queryset:
            call_command('mis_pull_schedules', f'--integration={integ.pk}', '--days=14')
        self.message_user(request, 'Готово. Лог — в IntegrationEvent.', level=messages.SUCCESS)


@admin.register(IntegrationEvent)
class IntegrationEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'integration', 'direction', 'kind', 'status', 'http_code')
    list_filter = ('direction', 'status', 'kind')
    search_fields = ('kind', 'error')
    autocomplete_fields = ('integration',)
    readonly_fields = ('integration', 'direction', 'kind', 'status', 'http_code',
                       'payload', 'response', 'error', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(ExternalMapping)
class ExternalMappingAdmin(admin.ModelAdmin):
    list_display = ('integration', 'local_kind', 'local_id', 'external_id', 'external_kind', 'updated_at')
    list_filter = ('local_kind', 'integration')
    search_fields = ('external_id', 'local_id')
    autocomplete_fields = ('integration',)


@admin.register(ScheduleSlot)
class ScheduleSlotAdmin(admin.ModelAdmin):
    list_display = ('vet', 'starts_at', 'duration_min', 'is_available', 'integration')
    list_filter = ('is_available', 'integration')
    autocomplete_fields = ('vet', 'integration')
    date_hierarchy = 'starts_at'


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('visited_at', 'pet', 'vet', 'total', 'integration')
    list_filter = ('integration',)
    autocomplete_fields = ('appointment', 'pet', 'vet', 'integration')
    readonly_fields = ('raw_payload', 'created_at', 'updated_at')
    date_hierarchy = 'visited_at'
