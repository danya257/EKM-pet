# pets/forms.py
from django import forms
from .models import Pet

class PetForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ['name', 'species', 'breed', 'birth_date', 'chip_number', 'photo']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }