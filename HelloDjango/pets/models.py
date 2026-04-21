# pets/models.py
import uuid
import os
from django.db import models
from django.urls import reverse
from users.models import User

class Pet(models.Model):
    SPECIES_CHOICES = [
        ('dog', 'Собака'),
        ('cat', 'Кошка'),
        ('bird', 'Птица'),
        ('rodent', 'Грызун'),
        ('rabbit', 'Кролик'),
        ('reptile', 'Рептилия'),
        ('other', 'Другое'),
    ]

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='pets',
        limit_choices_to={'user_type': 'owner'},
        verbose_name='Владелец'
    )
    name = models.CharField('Имя', max_length=100)
    species = models.CharField('Вид', max_length=20, choices=SPECIES_CHOICES)
    breed = models.CharField('Порода', max_length=100, blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    chip_number = models.CharField('Номер чипа', max_length=50, unique=True, blank=True, null=True)
    photo = models.ImageField('Фото питомца', upload_to='pets/photos/', blank=True, null=True)
    qr_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='UUID для QR')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')

    class Meta:
        verbose_name = 'Питомец'
        verbose_name_plural = 'Питомцы'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_species_display()})"

    def get_absolute_url(self):
        return reverse('pets:pet_detail', kwargs={'pk': self.pk})

    @property
    def qr_url(self):
        # URL для публичной страницы (без авторизации)
        return reverse('pets:pet_qr_view', kwargs={'uuid': self.qr_uuid})


def document_upload_path(instance, filename):
    """Путь загрузки: documents/pet_<id>/<category>/<filename>"""
    ext = os.path.splitext(filename)[1].lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return f"documents/pet_{instance.pet.pk}/{instance.category}/{safe_name}"


class PetDocument(models.Model):
    CATEGORY_CHOICES = [
        ('vaccination', 'Прививки'),
        ('analysis',    'Анализы'),
        ('surgery',     'Операции'),
        ('prescription','Рецепты'),
        ('certificate', 'Справки'),
        ('other',       'Другое'),
    ]

    pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Питомец'
    )
    category = models.CharField(
        'Категория',
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other'
    )
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    file = models.FileField(
        'Файл',
        upload_to=document_upload_path,
        help_text='PDF, JPG, PNG — до 10 МБ'
    )
    date = models.DateField('Дата документа', null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Загружен')

    class Meta:
        verbose_name = 'Документ питомца'
        verbose_name_plural = 'Документы питомцев'
        ordering = ['-date', '-uploaded_at']

    def __str__(self):
        return f"{self.get_category_display()}: {self.title}"

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def is_image(self):
        ext = os.path.splitext(self.file.name)[1].lower()
        return ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp')

    @property
    def is_pdf(self):
        return os.path.splitext(self.file.name)[1].lower() == '.pdf'