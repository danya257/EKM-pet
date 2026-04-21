from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import make_password, check_password


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
    pin_hash = models.CharField(
        _('PIN-код (хэш)'),
        max_length=128,
        blank=True,
        null=True,
        help_text=_('Хэш 4-значного PIN-кода для быстрого входа')
    )
    pin_enabled = models.BooleanField(
        _('PIN включён'),
        default=False
    )

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_user_type_display()})"

    def set_pin(self, raw_pin: str):
        """Сохраняет хэш PIN-кода."""
        self.pin_hash = make_password(raw_pin)
        self.pin_enabled = True

    def check_pin(self, raw_pin: str) -> bool:
        """Проверяет PIN-код."""
        if not self.pin_enabled or not self.pin_hash:
            return False
        return check_password(raw_pin, self.pin_hash)

    def clear_pin(self):
        """Удаляет PIN-код."""
        self.pin_hash = None
        self.pin_enabled = False