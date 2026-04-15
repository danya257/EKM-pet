# clinics/models.py
from django.db import models
from users.models import User

class Clinic(models.Model):
    name = models.CharField('Название клиники', max_length=200)
    address = models.TextField('Адрес')
    phone = models.CharField('Телефон', max_length=20, blank=True)
    email = models.EmailField('Email', blank=True)
    website = models.URLField('Сайт', blank=True)
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')

    # Администраторы клиники — пользователи с user_type = 'clinic_admin'
    admins = models.ManyToManyField(
        User,
        related_name='managed_clinics',
        limit_choices_to={'user_type__in': ['clinic_admin', 'vet']},
        verbose_name='Администраторы'
    )

    class Meta:
        verbose_name = 'Клиника'
        verbose_name_plural = 'Клиники'
        ordering = ['name']

    def __str__(self):
        return self.name