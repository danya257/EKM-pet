# medical_records/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from pets.models import Pet
from users.models import User

class MedicalRecord(models.Model):
    RECORD_TYPE_CHOICES = [
        ('vaccination', _('Вакцинация')),
        ('diagnosis', _('Диагноз')),
        ('procedure', _('Процедура')),
        ('lab_test', _('Лабораторный анализ')),
        ('medication', _('Назначение лекарств')),
        ('note', _('Заметка')),
        ('surgery', _('Операция')),
    ]

    pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name='medical_records',
        verbose_name=_('Питомец')
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Автор записи')
    )
    record_type = models.CharField(
        _('Тип записи'),
        max_length=20,
        choices=RECORD_TYPE_CHOICES
    )
    title = models.CharField(_('Заголовок'), max_length=200)
    description = models.TextField(_('Описание'), blank=True)
    date = models.DateField(_('Дата события'))
    document = models.FileField(
        _('Документ (PDF, фото)'),
        upload_to='medical_records/',
        blank=True,
        null=True,
        help_text=_('Опционально: фото чека, анализа, сертификата и т.д.')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))

    class Meta:
        verbose_name = _('Медицинская запись')
        verbose_name_plural = _('Медицинские записи')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_record_type_display()}: {self.title} ({self.date})"