from django import forms

from pets.models import Pet
from services.models import Service

from .models import Appointment


class AppointmentForm(forms.ModelForm):
    scheduled_at = forms.DateTimeField(
        label='Когда',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
    )

    class Meta:
        model = Appointment
        fields = ['pet', 'service', 'scheduled_at', 'kind', 'reason', 'contact_phone']
        widgets = {
            'reason': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Опишите коротко повод визита',
            }),
            'contact_phone': forms.TextInput(attrs={'placeholder': '+7 …'}),
        }

    def __init__(self, *args, vet=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vet = vet
        if user is not None:
            self.fields['pet'].queryset = Pet.objects.filter(owner=user)
        else:
            self.fields['pet'].queryset = Pet.objects.none()
        if vet is not None and vet.clinic_id:
            self.fields['service'].queryset = Service.objects.filter(clinic=vet.clinic)
        else:
            self.fields['service'].queryset = Service.objects.all()
        self.fields['service'].required = False
        self.fields['pet'].required = False
