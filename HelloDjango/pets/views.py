# pets/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Pet
from .forms import PetForm
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

class PetListView(LoginRequiredMixin, ListView):
    model = Pet
    template_name = 'pets/pet_list.html'
    context_object_name = 'pets'

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'owner':
            raise PermissionDenied("Только владельцы могут просматривать питомцев.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)

# Детальная страница (для владельца)
class PetDetailView(DetailView):
    model = Pet
    template_name = 'pets/pet_detail.html'
    context_object_name = 'pet'

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)

# Создание нового питомца
class PetCreateView(CreateView):
    model = Pet
    form_class = PetForm
    template_name = 'pets/pet_form.html'
    success_url = reverse_lazy('pets:pet_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Питомец успешно добавлен!')
        return super().form_valid(form)

# Редактирование питомца
class PetUpdateView(UpdateView):
    model = Pet
    form_class = PetForm
    template_name = 'pets/pet_form.html'
    success_url = reverse_lazy('pets:pet_list')

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Данные питомца успешно обновлены!')
        return super().form_valid(form)

# Публичная страница по QR (без авторизации!)
def pet_qr_view(request, uuid):
    pet = get_object_or_404(Pet, qr_uuid=uuid)
    return render(request, 'pets/pet_qr.html', {'pet': pet})


import qrcode
from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone
from django.conf import settings

def pet_qr_download(request, uuid):
    pet = get_object_or_404(Pet, qr_uuid=uuid)
    
    full_url = request.build_absolute_uri(pet.qr_url)
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(full_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type="image/png")
    filename = f"vetpassport_{pet.name}_{timezone.now().strftime('%Y%m%d')}.png"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response