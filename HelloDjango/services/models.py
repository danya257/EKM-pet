# services/models.py
from django.db import models
from clinics.models import Clinic
from users.models import User

class Service(models.Model):
    """Услуга, предоставляемая клиникой"""
    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name='Клиника'
    )
    name = models.CharField('Название услуги', max_length=200)
    description = models.TextField('Описание', blank=True)
    price = models.DecimalField('Цена (руб.)', max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} — {self.clinic.name}"


class ServiceAssignment(models.Model):
    """Связь услуги с ветеринаром и временными слотами"""
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    vet = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type__in': ['vet', 'clinic_admin']},
        verbose_name='Ветеринар'
    )
    # Слоты: список в формате [{"date": "2025-12-25", "times": ["10:00", "11:00"]}]
    available_slots = models.JSONField('Доступные слоты', default=list)

    class Meta:
        verbose_name = 'Назначение услуги'
        verbose_name_plural = 'Назначения услуг'
        unique_together = ('service', 'vet')

    def __str__(self):
        return f"{self.service.name} → {self.vet.username}"