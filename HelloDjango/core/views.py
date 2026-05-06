# core/views.py
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, RedirectView
from django.urls import reverse
from django.shortcuts import redirect
from django.db.models import Count

from users.models import User
from pets.models import Pet, PetDocument


class HomeView(TemplateView):
    template_name = 'core/home.html'


def landing_view(request):
    """Главная страница: лендинг с живыми числами из БД."""
    stats = {
        'users': User.objects.filter(is_superuser=False).count(),
        'pets': Pet.objects.count(),
        'docs': PetDocument.objects.count(),
    }
    return render(request, 'core/landing.html', {'stats': stats})

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