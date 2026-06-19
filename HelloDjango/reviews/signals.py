from decimal import Decimal
from django.db.models import Avg, Count
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Review


def _recalc_clinic(clinic):
    if clinic is None:
        return
    agg = Review.objects.filter(clinic=clinic, is_published=True).aggregate(
        avg=Avg('rating'), cnt=Count('id'),
    )
    clinic.rating = Decimal(str(round(agg['avg'] or 0, 2)))
    clinic.reviews_count = agg['cnt'] or 0
    clinic.save(update_fields=['rating', 'reviews_count'])


def _recalc_vet(vet):
    if vet is None:
        return
    agg = Review.objects.filter(vet=vet, is_published=True).aggregate(
        avg=Avg('rating'), cnt=Count('id'),
    )
    vet.rating = Decimal(str(round(agg['avg'] or 0, 2)))
    vet.reviews_count = agg['cnt'] or 0
    vet.save(update_fields=['rating', 'reviews_count'])


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def update_rating_aggregates(sender, instance, **kwargs):
    _recalc_clinic(instance.clinic)
    _recalc_vet(instance.vet)
