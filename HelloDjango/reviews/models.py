from django.conf import settings
from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    """Отзыв на клинику или врача. Объект-цель — одна из двух (XOR)."""

    TARGET_CLINIC = 'clinic'
    TARGET_VET = 'vet'

    clinic = models.ForeignKey(
        'clinics.Clinic',
        on_delete=models.CASCADE,
        related_name='clinic_reviews',
        null=True, blank=True,
        verbose_name='Клиника',
    )
    vet = models.ForeignKey(
        'clinics.VetProfile',
        on_delete=models.CASCADE,
        related_name='vet_reviews',
        null=True, blank=True,
        verbose_name='Врач',
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviews_written',
        verbose_name='Автор',
    )

    rating = models.PositiveSmallIntegerField(
        'Оценка',
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    text = models.TextField('Текст отзыва')
    pros = models.CharField('Плюсы', max_length=300, blank=True)
    cons = models.CharField('Минусы', max_length=300, blank=True)

    is_published = models.BooleanField('Опубликован', default=True)
    clinic_reply = models.TextField('Ответ клиники', blank=True)
    clinic_reply_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(clinic__isnull=False, vet__isnull=True) |
                    models.Q(clinic__isnull=True, vet__isnull=False)
                ),
                name='review_target_xor',
            )
        ]

    def __str__(self):
        target = self.vet or self.clinic
        return f'{self.rating}★ — {target}'

    @property
    def target(self):
        return self.vet or self.clinic

    @property
    def target_kind(self):
        return self.TARGET_VET if self.vet_id else self.TARGET_CLINIC

    def get_absolute_url(self):
        if self.vet_id:
            return reverse('clinics:public_vet_detail', kwargs={'pk': self.vet_id}) + '#reviews'
        return reverse('clinics:public_clinic_detail', kwargs={'pk': self.clinic_id}) + '#reviews'
