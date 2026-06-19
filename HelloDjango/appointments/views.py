from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView

from clinics.models import VetProfile

from .forms import AppointmentForm
from .models import Appointment


@login_required
def create_appointment(request, vet_pk):
    vet = get_object_or_404(VetProfile, pk=vet_pk, is_published=True)

    if request.method == 'POST':
        form = AppointmentForm(request.POST, vet=vet, user=request.user)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.vet = vet
            appt.clinic = vet.clinic
            appt.owner = request.user
            appt.save()
            messages.success(
                request,
                f'Заявка отправлена. {vet.display_name} свяжется с вами для подтверждения.',
            )
            return redirect('appointments:detail', pk=appt.pk)
    else:
        form = AppointmentForm(vet=vet, user=request.user)

    return render(request, 'appointments/appointment_form.html', {
        'form': form,
        'vet': vet,
    })


class AppointmentListView(LoginRequiredMixin, ListView):
    model = Appointment
    template_name = 'appointments/appointment_list.html'
    context_object_name = 'appointments'
    paginate_by = 20

    def get_queryset(self):
        return Appointment.objects.filter(owner=self.request.user).select_related('vet__user', 'clinic', 'pet', 'service')


class AppointmentDetailView(LoginRequiredMixin, DetailView):
    model = Appointment
    template_name = 'appointments/appointment_detail.html'
    context_object_name = 'appointment'

    def get_queryset(self):
        # Доступ — владельцу записи или назначенному врачу
        return Appointment.objects.filter(
            owner=self.request.user
        ) | Appointment.objects.filter(
            vet__user=self.request.user
        )
