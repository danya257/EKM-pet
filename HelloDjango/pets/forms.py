# pets/forms.py
from django import forms
from .models import Pet, PetDocument


class PetForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ['name', 'species', 'breed', 'birth_date', 'chip_number', 'photo']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }


class PetDocumentForm(forms.ModelForm):
    class Meta:
        model = PetDocument
        fields = ['category', 'title', 'description', 'file', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
