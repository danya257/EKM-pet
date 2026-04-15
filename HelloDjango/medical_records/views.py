# medical_records/views.py
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from pets.models import Pet
from .models import MedicalRecord
from .forms import MedicalRecordForm

# medical_records/views.py
class MedicalRecordCreateView(LoginRequiredMixin, CreateView):
    model = MedicalRecord
    form_class = MedicalRecordForm
    template_name = 'medical_records/record_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.pet = get_object_or_404(Pet, pk=self.kwargs['pet_pk'], owner=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pet'] = self.pet  # ← передаём pet в шаблон
        return context

    def form_valid(self, form):
        form.instance.pet = self.pet
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Запись добавлена!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('pets:pet_detail', kwargs={'pk': self.pet.pk})

class MedicalRecordDetailView(DetailView):
    model = MedicalRecord
    template_name = 'medical_records/record_detail.html'
    context_object_name = 'record'

    def get_queryset(self):
        # Позволяем смотреть запись только владельцу питомца
        return MedicalRecord.objects.filter(pet__owner=self.request.user)