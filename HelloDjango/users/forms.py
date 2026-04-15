# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserRegisterForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Убираем help_text
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None

        # Добавляем только класс
        for field in self.fields.values():
            field.widget.attrs.update({'class': ''})  # класс не нужен — стили через .input-group