# pets/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
import json

from .models import Pet, PetDocument
from .forms import PetForm, PetDocumentForm


# ─── Питомцы ─────────────────────────────────────────────────────────────────

class PetListView(LoginRequiredMixin, ListView):
    model = Pet
    template_name = 'pets/pet_list.html'
    context_object_name = 'pets'

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'owner':
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user).prefetch_related('documents', 'medical_records')


class PetDetailView(LoginRequiredMixin, DetailView):
    model = Pet
    template_name = 'pets/pet_detail.html'
    context_object_name = 'pet'

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pet = self.object
        ctx['documents_by_category'] = {}
        for cat_key, cat_label in PetDocument.CATEGORY_CHOICES:
            docs = pet.documents.filter(category=cat_key)
            if docs.exists():
                ctx['documents_by_category'][cat_label] = docs
        ctx['all_documents'] = pet.documents.all()
        ctx['records'] = pet.medical_records.all().order_by('-date')
        return ctx


class PetCreateView(LoginRequiredMixin, CreateView):
    model = Pet
    form_class = PetForm
    template_name = 'pets/pet_form.html'
    success_url = reverse_lazy('pets:pet_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, f'Питомец {form.instance.name} добавлен!')
        return super().form_valid(form)


class PetUpdateView(LoginRequiredMixin, UpdateView):
    model = Pet
    form_class = PetForm
    template_name = 'pets/pet_form.html'

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)

    def get_success_url(self):
        return reverse('pets:pet_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Данные питомца обновлены!')
        return super().form_valid(form)


class PetDeleteView(LoginRequiredMixin, DeleteView):
    model = Pet
    template_name = 'pets/pet_confirm_delete.html'
    success_url = reverse_lazy('pets:pet_list')

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, f'Питомец удалён.')
        return super().form_valid(form)


# ─── Документы ───────────────────────────────────────────────────────────────

class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = PetDocument
    form_class = PetDocumentForm
    template_name = 'pets/document_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.pet = get_object_or_404(Pet, pk=self.kwargs['pet_pk'], owner=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pet'] = self.pet
        return ctx

    def form_valid(self, form):
        form.instance.pet = self.pet
        messages.success(self.request, 'Документ загружен!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('pets:pet_detail', kwargs={'pk': self.pet.pk}) + '#documents'


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = PetDocument
    template_name = 'pets/document_confirm_delete.html'

    def get_queryset(self):
        return PetDocument.objects.filter(pet__owner=self.request.user)

    def get_success_url(self):
        return reverse('pets:pet_detail', kwargs={'pk': self.object.pet.pk}) + '#documents'

    def form_valid(self, form):
        messages.success(self.request, 'Документ удалён.')
        return super().form_valid(form)


# ─── QR-паспорт ──────────────────────────────────────────────────────────────

def pet_qr_view(request, uuid):
    pet = get_object_or_404(Pet, qr_uuid=uuid)
    return render(request, 'pets/pet_qr.html', {'pet': pet})


import qrcode
from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone


def pet_qr_download(request, uuid):
    pet = get_object_or_404(Pet, qr_uuid=uuid)
    full_url = request.build_absolute_uri(pet.qr_url)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(full_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#2d3748", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="image/png")
    filename = f"vetpassport_{pet.name}_{timezone.now().strftime('%Y%m%d')}.png"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
