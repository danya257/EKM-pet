from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('owner', _('Владелец')),
        ('vet', _('Ветеринар')),
        ('clinic_admin', _('Администратор клиники')),
    )
    user_type = models.CharField(
        _('Тип пользователя'),
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='owner'
    )

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_user_type_display()})"