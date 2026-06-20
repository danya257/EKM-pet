"""
Модели интеграционного слоя.

Каждая клиника может иметь одну активную интеграцию с МИС
(Vetmanager / 1С / generic). Все ext-id, лог обмена и слоты расписания
живут здесь, а не в основном домене — это держит clinics/ и appointments/
чистыми от транспорта.
"""
from __future__ import annotations

import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


# =========================================================================
#  1. Настройка интеграции
# =========================================================================

class ClinicIntegration(models.Model):
    """Подключение конкретной клиники к её МИС."""

    KIND_VETMANAGER = 'vetmanager'
    KIND_ONEC       = 'onec'
    KIND_WEBHOOK    = 'webhook'      # generic outbound webhook + REST API
    KIND_FHIR       = 'fhir'         # на будущее (HL7 FHIR)

    KIND_CHOICES = [
        (KIND_VETMANAGER, 'Vetmanager (REST API)'),
        (KIND_ONEC,       '1С:Медицина. Ветклиника'),
        (KIND_WEBHOOK,    'Generic webhook + REST'),
        (KIND_FHIR,       'HL7 FHIR'),
    ]

    clinic = models.OneToOneField(
        'clinics.Clinic',
        on_delete=models.CASCADE,
        related_name='integration',
        verbose_name='Клиника',
    )
    kind = models.CharField('Тип МИС', max_length=20, choices=KIND_CHOICES)

    # Подключение
    base_url = models.URLField('Base URL API', max_length=500, blank=True)
    api_token = models.CharField(
        'API-токен / OAuth secret',
        max_length=255, blank=True,
        help_text='Если МИС использует static-токен. Для OAuth — client_secret.',
    )
    oauth_client_id = models.CharField('OAuth client_id', max_length=128, blank=True)
    extra = models.JSONField(
        'Дополнительные параметры',
        default=dict, blank=True,
        help_text='Произвольный JSON: db_name для 1С, scope, иные настройки адаптера.',
    )

    # Inbound (МИС → нам): HMAC-секрет для подписи webhook'ов
    webhook_secret = models.CharField(
        'Webhook secret (HMAC SHA-256)',
        max_length=64, blank=True,
        help_text='Используется для подписи входящих POST. Генерируется автоматически.',
    )

    is_active = models.BooleanField('Активна', default=True)
    push_appointments  = models.BooleanField('Слать заявки в МИС',  default=True)
    pull_schedule      = models.BooleanField('Тянуть расписание',    default=True)
    pull_visits        = models.BooleanField('Тянуть итоги визитов', default=True)
    pull_services      = models.BooleanField('Тянуть прайс',         default=True)

    last_sync_at = models.DateTimeField('Последняя синхронизация', null=True, blank=True)
    last_error   = models.TextField('Последняя ошибка', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Интеграция клиники'
        verbose_name_plural = 'Интеграции клиник'

    def __str__(self):
        return f'{self.clinic.name} → {self.get_kind_display()}'

    def save(self, *args, **kwargs):
        if not self.webhook_secret:
            self.webhook_secret = secrets.token_hex(32)
        super().save(*args, **kwargs)

    @property
    def is_oauth(self) -> bool:
        return bool(self.oauth_client_id)


# =========================================================================
#  2. Лог обмена — каждый запрос/ответ в обе стороны
# =========================================================================

class IntegrationEvent(models.Model):
    """Аудит всех событий: что/когда/куда отправили, что/откуда пришло."""

    DIR_OUT = 'out'
    DIR_IN  = 'in'
    DIR_CHOICES = [(DIR_OUT, 'Исходящее'), (DIR_IN, 'Входящее')]

    STATUS_OK     = 'ok'
    STATUS_ERR    = 'error'
    STATUS_RETRY  = 'retry'
    STATUS_CHOICES = [
        (STATUS_OK,    'OK'),
        (STATUS_ERR,   'Ошибка'),
        (STATUS_RETRY, 'Повтор'),
    ]

    integration = models.ForeignKey(
        ClinicIntegration, on_delete=models.CASCADE, related_name='events',
        verbose_name='Интеграция',
    )
    direction = models.CharField('Направление', max_length=4, choices=DIR_CHOICES)
    kind      = models.CharField('Событие', max_length=64,
                                 help_text='appointment_push, schedule_pull, visit_in, ...')
    status    = models.CharField('Статус', max_length=8, choices=STATUS_CHOICES, default=STATUS_OK)
    http_code = models.PositiveSmallIntegerField('HTTP-код', null=True, blank=True)
    payload   = models.JSONField('Тело',     default=dict, blank=True)
    response  = models.JSONField('Ответ',    default=dict, blank=True)
    error     = models.TextField('Ошибка', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Событие интеграции'
        verbose_name_plural = 'События интеграции'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['integration', '-created_at']),
            models.Index(fields=['kind', 'status']),
        ]

    def __str__(self):
        return f'{self.created_at:%d.%m %H:%M} {self.direction} {self.kind} [{self.status}]'


# =========================================================================
#  3. Маппинг наших id ↔ внешних
# =========================================================================

class ExternalMapping(models.Model):
    """Связка локального объекта с его id во внешней МИС."""

    integration = models.ForeignKey(
        ClinicIntegration, on_delete=models.CASCADE, related_name='mappings',
    )
    # Что мапится — храним строкой 'appointments.appointment', 'pets.pet', и т.п.
    # Без GenericForeignKey, чтобы не таскать contenttypes для синков.
    local_kind = models.CharField('Локальный объект', max_length=64)
    local_id   = models.PositiveBigIntegerField('Локальный id')
    external_id = models.CharField('id в МИС', max_length=128)
    external_kind = models.CharField('Тип в МИС', max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Внешний id'
        verbose_name_plural = 'Внешние id (mapping)'
        unique_together = [
            ('integration', 'local_kind', 'local_id'),
            ('integration', 'local_kind', 'external_id'),
        ]

    def __str__(self):
        return f'{self.local_kind}#{self.local_id} ↔ {self.external_id}'


# =========================================================================
#  4. Слоты расписания (pull из МИС)
# =========================================================================

class ScheduleSlot(models.Model):
    """Свободный слот врача, импортированный из МИС."""

    vet = models.ForeignKey(
        'clinics.VetProfile', on_delete=models.CASCADE, related_name='slots',
        verbose_name='Врач',
    )
    integration = models.ForeignKey(
        ClinicIntegration, on_delete=models.CASCADE, related_name='slots',
        null=True, blank=True,
    )
    starts_at = models.DateTimeField('Начало', db_index=True)
    duration_min = models.PositiveSmallIntegerField('Длительность, мин', default=30)
    is_available = models.BooleanField('Свободен', default=True)
    external_id = models.CharField('id в МИС', max_length=128, blank=True)

    pulled_at = models.DateTimeField('Получен', default=timezone.now)

    class Meta:
        verbose_name = 'Слот расписания'
        verbose_name_plural = 'Слоты расписания'
        ordering = ['starts_at']
        indexes = [
            models.Index(fields=['vet', 'starts_at']),
            models.Index(fields=['is_available', 'starts_at']),
        ]
        unique_together = [('integration', 'external_id')]

    def __str__(self):
        return f'{self.vet} · {self.starts_at:%d.%m %H:%M}'


# =========================================================================
#  5. Итог визита (приходит из МИС после приёма)
# =========================================================================

class Visit(models.Model):
    """Что было сделано на приёме (приходит из МИС, попадает в карту питомца)."""

    appointment = models.OneToOneField(
        'appointments.Appointment',
        on_delete=models.CASCADE, related_name='visit',
        null=True, blank=True,
        verbose_name='Запись',
    )
    integration = models.ForeignKey(
        ClinicIntegration, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='visits',
    )

    # Базовые поля приёма (если МИС шлёт без appointment_id)
    pet = models.ForeignKey(
        'pets.Pet', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='visits',
    )
    vet = models.ForeignKey(
        'clinics.VetProfile', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='visits_done',
    )

    visited_at = models.DateTimeField('Дата визита')
    diagnosis = models.TextField('Диагноз', blank=True)
    treatment = models.TextField('Лечение / назначения', blank=True)
    services_done = models.JSONField('Услуги', default=list, blank=True,
                                     help_text='[{"name": "...", "price": 1500}, ...]')
    total = models.DecimalField('Итого, ₽', max_digits=10, decimal_places=2, default=0)

    # Документы — массив ссылок (PDF/JPG, выложенных МИС). При желании можно
    # докачать в наш MEDIA_ROOT отдельной задачей.
    documents = models.JSONField('Документы', default=list, blank=True,
                                 help_text='[{"url": "...", "title": "..."}, ...]')

    external_id = models.CharField('id в МИС', max_length=128, blank=True)
    raw_payload = models.JSONField('Сырой payload', default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Визит (из МИС)'
        verbose_name_plural = 'Визиты (из МИС)'
        ordering = ['-visited_at']

    def __str__(self):
        return f'{self.pet} · {self.visited_at:%d.%m.%Y}'
