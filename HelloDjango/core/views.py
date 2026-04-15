# core/views.py
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, RedirectView
from django.urls import reverse
from django.shortcuts import redirect

class HomeView(TemplateView):
    template_name = 'core/home.html'

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