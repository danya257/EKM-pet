from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        label='Оценка',
        choices=[(i, f'{i}★') for i in range(5, 0, -1)],
        coerce=int,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Review
        fields = ['rating', 'text', 'pros', 'cons']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Подробно расскажите о визите…'}),
            'pros': forms.TextInput(attrs={'placeholder': 'Что понравилось'}),
            'cons': forms.TextInput(attrs={'placeholder': 'Что можно улучшить'}),
        }
        labels = {
            'text': 'Отзыв',
        }
