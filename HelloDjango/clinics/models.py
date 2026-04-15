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
    working_hours = models.TextField('Часы работы', blank=True, help_text='Например: Пн-Пт 9:00-20:00, Сб-Вс 10:00-18:00')
    reviews = models.TextField('Отзывы', blank=True, help_text='Отзывы клиентов о клинике (если нет ID Яндекс Карт)')
    rating = models.DecimalField('Рейтинг', max_digits=3, decimal_places=2, default=0, help_text='Рейтинг от 0 до 5')
    yandex_maps_id = models.CharField('ID Яндекс Карт', max_length=50, blank=True, help_text='ID клиники на Яндекс Картах для виджета отзывов (например: 8738718516)')
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