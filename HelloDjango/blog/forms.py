# blog/forms.py
from django import forms
from .models import Article

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'slug', 'content', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'naprimer-kak-pravilno-kormit-sobaku'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 15}),
        }