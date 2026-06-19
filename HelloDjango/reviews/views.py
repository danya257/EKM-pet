from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from clinics.models import Clinic, VetProfile

from .forms import ReviewForm


@login_required
def add_review(request, target_kind, pk):
    if target_kind == 'clinic':
        target = get_object_or_404(Clinic, pk=pk)
        ctx_kwargs = {'clinic': target}
    elif target_kind == 'vet':
        target = get_object_or_404(VetProfile, pk=pk)
        ctx_kwargs = {'vet': target}
    else:
        return redirect('clinics:public_clinic_list')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.author = request.user
            for k, v in ctx_kwargs.items():
                setattr(review, k, v)
            review.save()
            messages.success(request, 'Спасибо за отзыв!')
            return redirect(target.get_absolute_url() + '#reviews')
    else:
        form = ReviewForm()

    return render(request, 'reviews/review_form.html', {
        'form': form,
        'target': target,
        'target_kind': target_kind,
    })
