# clinics/forms.py
from django import forms
from .models import Clinic
from users.models import User

class ClinicForm(forms.ModelForm):
    class Meta:
        model = Clinic
        fields = ['name', 'address', 'phone', 'email', 'website', 'description', 'admins']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'admins': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['admins'].queryset = User.objects.filter(
            user_type__in=['clinic_admin', 'vet']
        )