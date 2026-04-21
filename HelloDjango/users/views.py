# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
import json

from .models import User


# ─── Логин ───────────────────────────────────────────────────────────────────

class OwnerLoginView(LoginView):
    template_name = 'users/login.html'

    def get_success_url(self):
        return reverse_lazy('pets:pet_list')

    def form_invalid(self, form):
        form.add_error(None, "Неверное имя пользователя или пароль")
        return super().form_invalid(form)


class ClinicLoginView(LoginView):
    template_name = 'users/login.html'

    def get_success_url(self):
        return reverse_lazy('core:dashboard')

    def form_invalid(self, form):
        form.add_error(None, "Неверное имя пользователя или пароль")
        return super().form_invalid(form)


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = AuthenticationForm

    def get_success_url(self):
        user = self.request.user
        if user.user_type == 'owner':
            return reverse_lazy('pets:pet_list')
        return reverse_lazy('core:dashboard')

    def form_valid(self, response):
        # После успешного входа — предлагаем настроить PIN если не настроен
        result = super().form_valid(response)
        if not self.request.user.pin_enabled:
            self.request.session['suggest_pin'] = True
        return result

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['username'].widget.attrs.update({'autocomplete': 'username'})
        form.fields['password'].widget.attrs.update({'autocomplete': 'current-password'})
        return form


class CustomLogoutView(LogoutView):
    http_method_names = ['post', 'get']

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET':
            from django.contrib.auth import logout
            logout(request)
            return redirect('blog:home')
        return super().dispatch(request, *args, **kwargs)


# ─── Регистрация ──────────────────────────────────────────────────────────────

class UserRegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email',
                  'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None

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
        messages.success(self.request, 'Аккаунт создан! Войдите в систему.')
        return super().form_valid(form)


# ─── Профиль ─────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    suggest_pin = request.session.pop('suggest_pin', False)
    return render(request, 'users/profile.html', {'suggest_pin': suggest_pin})


# ─── PIN-код ──────────────────────────────────────────────────────────────────

def pin_login_view(request):
    """Вход по PIN-коду. GET — форма, POST — проверка."""
    username = request.session.get('pin_username')

    if request.method == 'POST':
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        pin = data.get('pin', '')
        username = data.get('username') or username

        if not username:
            return JsonResponse({'ok': False, 'error': 'Сессия истекла'}, status=400)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Пользователь не найден'}, status=400)

        if user.check_pin(pin):
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            next_url = reverse('pets:pet_list') if user.user_type == 'owner' else reverse('core:dashboard')
            return JsonResponse({'ok': True, 'redirect': next_url})
        else:
            return JsonResponse({'ok': False, 'error': 'Неверный PIN'}, status=400)

    # GET — показываем форму PIN
    if not username:
        return redirect('users:login')
    return render(request, 'users/pin_login.html', {'username': username})


@login_required
@require_POST
def pin_setup_view(request):
    """Установка или смена PIN-кода."""
    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    pin = data.get('pin', '')

    if not pin.isdigit() or len(pin) != 4:
        return JsonResponse({'ok': False, 'error': 'PIN должен быть 4 цифры'}, status=400)

    request.user.set_pin(pin)
    request.user.save(update_fields=['pin_hash', 'pin_enabled'])
    # Сохраняем username в сессии для последующего PIN-входа
    request.session['pin_username'] = request.user.username
    return JsonResponse({'ok': True, 'message': 'PIN установлен'})


@login_required
@require_POST
def pin_disable_view(request):
    """Отключение PIN-кода."""
    request.user.clear_pin()
    request.user.save(update_fields=['pin_hash', 'pin_enabled'])
    request.session.pop('pin_username', None)
    return JsonResponse({'ok': True, 'message': 'PIN отключён'})
