# core/views.py
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, RedirectView
from django.urls import reverse
from django.shortcuts import redirect
from django.db.models import Count

from users.models import User
from pets.models import Pet, PetDocument
from clinics.models import Clinic, VetProfile, Specialization


class HomeView(TemplateView):
    template_name = 'core/home.html'


def landing_view(request):
    """Главная: лендинг каталога ветпомощи."""
    stats = {
        'clinics': Clinic.objects.count(),
        'vets':    VetProfile.objects.filter(is_published=True).count(),
        'reviews': __import__('reviews').models.Review.objects.filter(is_published=True).count() if Clinic.objects.exists() else 0,
        'users':   User.objects.filter(is_superuser=False).count(),
        'pets':    Pet.objects.count(),
    }
    ctx = {
        'stats':       stats,
        'top_vets':    VetProfile.objects.filter(is_published=True).select_related('user', 'clinic').prefetch_related('specializations').order_by('-rating', '-reviews_count')[:6],
        'top_clinics': Clinic.objects.order_by('-rating', '-reviews_count')[:4],
        'specs':       Specialization.objects.all()[:8],
        'cities':      list(Clinic.objects.exclude(city='').values_list('city', flat=True).distinct().order_by('city')),
    }
    return render(request, 'core/landing.html', ctx)

class DashboardRedirectView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if user.user_type == 'owner':
            return reverse('pets:pet_list')
        elif user.user_type in ['vet', 'clinic_admin']:
            return reverse('clinics:dashboard')  # ← именно так
        return reverse('blog:home')

class RoleBasedRedirectView(LoginRequiredMixin, RedirectView):
    """Перенаправление после входа в зависимости от роли."""
    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if user.user_type == 'owner':
            return reverse('pets:pet_list')
        elif user.user_type in ['vet', 'clinic_admin']:
            return reverse('clinics:clinic_list')
        else:
            return reverse('core:home')  # fallback