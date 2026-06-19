# clinics/models.py
from django.db import models
from django.urls import reverse
from users.models import User


class Specialization(models.Model):
    """Специализация ветеринара (терапевт, хирург, кардиолог, экзотика и т.д.)"""
    name = models.CharField('Название', max_length=80, unique=True)
    slug = models.SlugField('Слаг', max_length=80, unique=True)
    icon = models.CharField('Эмодзи-иконка', max_length=8, blank=True, default='🩺')
    description = models.CharField('Описание', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Специализация'
        verbose_name_plural = 'Специализации'
        ordering = ['name']

    def __str__(self):
        return self.name


class Clinic(models.Model):
    name = models.CharField('Название клиники', max_length=200)
    city = models.CharField('Город', max_length=100, blank=True, db_index=True)
    address = models.TextField('Адрес')
    phone = models.CharField('Телефон', max_length=20, blank=True)
    email = models.EmailField('Email', blank=True)
    website = models.URLField('Сайт', blank=True)
    description = models.TextField('Описание', blank=True)
    working_hours = models.TextField('Часы работы', blank=True, help_text='Например: Пн-Пт 9:00-20:00, Сб-Вс 10:00-18:00')
    # Старое текстовое поле reviews оставлено для обратной совместимости с миграциями;
    # реальные отзывы теперь в модели reviews.Review.
    reviews = models.TextField('Отзывы (legacy)', blank=True)
    rating = models.DecimalField('Рейтинг (агрегат)', max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField('Отзывов', default=0)
    yandex_maps_id = models.CharField('ID Яндекс Карт', max_length=50, blank=True)
    photo = models.ImageField('Фото клиники', upload_to='clinics/photos/', blank=True, null=True)
    is_24h = models.BooleanField('Круглосуточно', default=False)
    accepts_online = models.BooleanField('Онлайн-консультации', default=False)
    has_lab = models.BooleanField('Своя лаборатория', default=False)
    has_surgery = models.BooleanField('Хирургия', default=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')

    admins = models.ManyToManyField(
        User,
        related_name='managed_clinics',
        limit_choices_to={'user_type__in': ['clinic_admin', 'vet']},
        verbose_name='Администраторы'
    )

    class Meta:
        verbose_name = 'Клиника'
        verbose_name_plural = 'Клиники'
        ordering = ['-rating', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('clinics:public_clinic_detail', kwargs={'pk': self.pk})


class VetProfile(models.Model):
    """Публичный профиль врача — данные, которые видит владелец на сайте-каталоге."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='vet_profile',
        limit_choices_to={'user_type__in': ['vet', 'clinic_admin']},
        verbose_name='Учётка'
    )
    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vets',
        verbose_name='Клиника'
    )
    specializations = models.ManyToManyField(
        Specialization,
        related_name='vets',
        verbose_name='Специализации',
        blank=True,
    )
    photo = models.ImageField('Фото', upload_to='vets/photos/', blank=True, null=True)
    experience_years = models.PositiveSmallIntegerField('Опыт, лет', default=0)
    education = models.TextField('Образование', blank=True)
    bio = models.TextField('О себе', blank=True)
    price_consultation = models.DecimalField('Цена приёма, ₽', max_digits=8, decimal_places=2, default=0)
    accepts_online = models.BooleanField('Онлайн-консультации', default=False)
    accepts_house_call = models.BooleanField('Выезд на дом', default=False)
    rating = models.DecimalField('Рейтинг (агрегат)', max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField('Отзывов', default=0)
    is_published = models.BooleanField('Публиковать в каталоге', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Профиль врача'
        verbose_name_plural = 'Профили врачей'
        ordering = ['-rating', 'user__last_name']

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def display_name(self):
        full = self.user.get_full_name()
        return full or self.user.username

    def get_absolute_url(self):
        return reverse('clinics:public_vet_detail', kwargs={'pk': self.pk})