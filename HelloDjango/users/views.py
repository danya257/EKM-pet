# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.forms import UserCreationForm
from .models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

class OwnerLoginView(LoginView):
    template_name = 'users/login_owner.html'

    def get_success_url(self):
        return reverse_lazy('core:dashboard')

    def form_invalid(self, form):
        form.add_error(None, "Неверное имя пользователя или пароль")
        return super().form_invalid(form)

class ClinicLoginView(LoginView):
    template_name = 'users/login_clinic.html'

    def get_success_url(self):
        return reverse_lazy('core:dashboard')

    def form_invalid(self, form):
        form.add_error(None, "Неверное имя пользователя или пароль")
        return super().form_invalid(form)

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = AuthenticationForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['username'].widget.attrs.update({'class': 'form-control'})
        form.fields['password'].widget.attrs.update({'class': 'form-control'})
        return form

class UserRegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'owner' 
        if commit:
            user.save()
        return user

class RegisterView(CreateView):
    form_class = UserRegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        return response

def profile_view(request):
    return render(request, 'users/profile.html')