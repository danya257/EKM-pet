from django.conf import settings
from django.db import models
from django.urls import reverse


class Appointment(models.Model):
    """Запись владельца к врачу."""

    STATUS_NEW = 'new'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_DONE = 'done'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_NEW,       'Новая заявка'),
        (STATUS_CONFIRMED, 'Подтверждена'),
        (STATUS_DONE,      'Завершена'),
        (STATUS_CANCELLED, 'Отменена'),
    ]

    KIND_OFFLINE = 'offline'
    KIND_ONLINE = 'online'
    KIND_HOUSE = 'house_call'
    KIND_CHOICES = [
        (KIND_OFFLINE, 'В клинике'),
        (KIND_ONLINE,  'Онлайн'),
        (KIND_HOUSE,   'На дому'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name='Владелец',
    )
    pet = models.ForeignKey(
        'pets.Pet',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='appointments',
        verbose_name='Питомец',
    )
    vet = models.ForeignKey(
        'clinics.VetProfile',
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name='Врач',
    )
    clinic = models.ForeignKey(
        'clinics.Clinic',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='appointments',
        verbose_name='Клиника',
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='appointments',
        verbose_name='Услуга',
    )

    scheduled_at = models.DateTimeField('Дата и время')
    kind = models.CharField('Формат', max_length=20, choices=KIND_CHOICES, default=KIND_OFFLINE)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)

    reason = models.TextField('Причина обращения', blank=True)
    vet_note = models.TextField('Заметка врача', blank=True)
    contact_phone = models.CharField('Контактный телефон', max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Запись на приём'
        verbose_name_plural = 'Записи на приём'
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['vet', 'scheduled_at']),
            models.Index(fields=['owner', 'scheduled_at']),
        ]

    def __str__(self):
        return f'{self.vet} · {self.scheduled_at:%d.%m.%Y %H:%M}'

    def get_absolute_url(self):
        return reverse('appointments:detail', kwargs={'pk': self.pk})

    @property
    def is_upcoming(self):
        from django.utils import timezone
        return self.status in (self.STATUS_NEW, self.STATUS_CONFIRMED) and self.scheduled_at >= timezone.now()
