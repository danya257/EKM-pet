# services/forms.py
from django import forms
from .models import Service, ServiceAssignment
from users.models import User
from clinics.models import Clinic

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ServiceAssignmentForm(forms.ModelForm):
    class Meta:
        model = ServiceAssignment
        fields = ['vet', 'available_slots']
        widgets = {
            'vet': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, clinic, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Только ветеринары этой клиники
        self.fields['vet'].queryset = clinic.admins.filter(
            user_type__in=['vet', 'clinic_admin']
        )
        # JSON-поле будем редактировать вручную (для диплома — текстовое поле)
        self.fields['available_slots'] = forms.CharField(
            widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            help_text='Формат: [{"date": "2025-12-25", "times": ["10:00", "11:00"]}]'
        )

    def clean_available_slots(self):
        import json
        data = self.cleaned_data['available_slots']
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError("Неверный формат JSON.")