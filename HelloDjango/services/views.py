# services/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import Service, ServiceAssignment
from .forms import ServiceForm, ServiceAssignmentForm
from clinics.models import Clinic

@login_required
def service_list_view(request, clinic_id):
    """Список услуг клиники (для владельца клиники)"""
    clinic = get_object_or_404(Clinic, id=clinic_id)
    if request.user not in clinic.admins.all():
        raise PermissionDenied("Доступ запрещён")
    
    services = clinic.services.all()
    return render(request, 'services/service_list.html', {
        'clinic': clinic,
        'services': services
    })

@login_required
def service_create_view(request, clinic_id):
    """Создание новой услуги"""
    clinic = get_object_or_404(Clinic, id=clinic_id)
    if request.user not in clinic.admins.all():
        raise PermissionDenied()

    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.clinic = clinic
            service.save()
            return redirect('services:service_detail', clinic_id=clinic.id, service_id=service.id)
    else:
        form = ServiceForm()
    return render(request, 'services/service_form.html', {
        'form': form,
        'clinic': clinic,
        'title': 'Добавить услугу'
    })

@login_required
def service_detail_view(request, clinic_id, service_id):
    """Детали услуги + назначения"""
    clinic = get_object_or_404(Clinic, id=clinic_id)
    service = get_object_or_404(Service, id=service_id, clinic=clinic)
    if request.user not in clinic.admins.all():
        raise PermissionDenied()

    assignments = service.assignments.all()
    return render(request, 'services/service_detail.html', {
        'clinic': clinic,
        'service': service,
        'assignments': assignments
    })

@login_required
def assignment_create_view(request, clinic_id, service_id):
    """Назначить ветеринара на услугу"""
    clinic = get_object_or_404(Clinic, id=clinic_id)
    service = get_object_or_404(Service, id=service_id, clinic=clinic)
    if request.user not in clinic.admins.all():
        raise PermissionDenied()

    if request.method == 'POST':
        form = ServiceAssignmentForm(clinic, request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.service = service
            assignment.save()
            return redirect('services:service_detail', clinic_id=clinic.id, service_id=service.id)
    else:
        form = ServiceAssignmentForm(clinic)
    return render(request, 'services/assignment_form.html', {
        'form': form,
        'clinic': clinic,
        'service': service
    })