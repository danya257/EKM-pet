# clinics/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, TemplateView
)
from django.urls import reverse_lazy
from django.contrib.auth import login
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count, Q, Prefetch
from django.utils import timezone

from users.models import User
from .models import Clinic, Specialization, VetProfile
from .forms import ClinicForm
from services.models import Service, ServiceAssignment
from pets.models import Pet
from medical_records.models import MedicalRecord
from chat.models import Message
from reviews.models import Review


# === Dashboard для клиник ===
class ClinicDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'clinics/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.user_type not in ['vet', 'clinic_admin']:
            raise PermissionDenied("Доступ запрещён")

        clinics = Clinic.objects.filter(admins=user)
        context['clinics'] = clinics

        if clinics.exists():
            # Все пользователи (ветеринары), связанные с этими клиниками
            vet_ids = User.objects.filter(
                managed_clinics__in=clinics
            ).values_list('id', flat=True)

            # 1. Питомцы с записями от этих ветеринаров
            pets_count = Pet.objects.filter(
                medical_records__created_by__in=vet_ids
            ).distinct().count()

            # 2. Непрочитанные сообщения
            unread_messages = Message.objects.filter(
                chat__vet=user,
                is_read=False
            ).count()

            # 3. Записи за последнюю неделю
            week_ago = timezone.now() - timezone.timedelta(days=7)
            recent_records = MedicalRecord.objects.filter(
                created_by__in=vet_ids,
                created_at__gte=week_ago
            ).count()

            context.update({
                'pets_count': pets_count,
                'unread_messages': unread_messages,
                'recent_records': recent_records,
            })

        return context


# === Управление клиниками (личный кабинет) ===
class ClinicListView(LoginRequiredMixin, ListView):
    model = Clinic
    template_name = 'clinics/clinic_list.html'
    context_object_name = 'clinics'

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type not in ['vet', 'clinic_admin']:
            raise PermissionDenied("Только сотрудники клиник могут просматривать этот раздел.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Clinic.objects.filter(admins=self.request.user)


class ClinicDetailView(LoginRequiredMixin, DetailView):
    model = Clinic
    template_name = 'clinics/clinic_detail.html'
    context_object_name = 'clinic'

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type not in ['vet', 'clinic_admin']:
            raise PermissionDenied("Доступ запрещён.")
        return super().dispatch(request, *args, **kwargs)


class ClinicCreateView(LoginRequiredMixin, CreateView):
    model = Clinic
    form_class = ClinicForm
    template_name = 'clinics/clinic_form.html'
    success_url = reverse_lazy('clinics:clinic_list')

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'clinic_admin':
            raise PermissionDenied("Только администраторы клиник могут создавать клиники.")
        return super().dispatch(request, *args, **kwargs)


# === Регистрация клиники ===
class ClinicRegisterForm(UserCreationForm):
    clinic_name = forms.CharField(
        max_length=200,
        label='Название ветеринарной клиники',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    clinic_address = forms.CharField(
        label='Адрес клиники',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'clinic_admin'
        if commit:
            user.save()
        return user


class ClinicRegisterView(CreateView):
    form_class = ClinicRegisterForm
    template_name = 'clinics/clinic_register.html'
    success_url = reverse_lazy('clinics:clinic_list')

    def form_valid(self, form):
        user = form.save()
        clinic = Clinic.objects.create(
            name=form.cleaned_data['clinic_name'],
            address=form.cleaned_data['clinic_address']
        )
        clinic.admins.add(user)
        login(self.request, user)
        return redirect(self.success_url)


# === Услуги ===
class ServiceListView(LoginRequiredMixin, ListView):
    template_name = 'clinics/service_list.html'
    context_object_name = 'services'

    def get_queryset(self):
        user = self.request.user
        self.clinic = Clinic.objects.filter(admins=user).first()  # ← сохраняем клинику
        if not self.clinic:
            raise PermissionDenied
        return Service.objects.filter(clinic=self.clinic)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clinic'] = self.clinic  # ← передаём в шаблон
        return context


class ServiceCreateView(LoginRequiredMixin, CreateView):
    model = Service
    fields = ['name', 'description', 'price']
    template_name = 'clinics/service_form.html'

    def form_valid(self, form):
        clinic = Clinic.objects.filter(admins=self.request.user).first()
        if not clinic:
            raise PermissionDenied
        form.instance.clinic = clinic
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('clinics:service_list')


class ServiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Service
    fields = ['name', 'description', 'price']
    template_name = 'clinics/service_form.html'
    success_url = reverse_lazy('clinics:service_list')

    def dispatch(self, request, *args, **kwargs):
        service = self.get_object()
        if request.user not in service.clinic.admins.all():
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


# === Ветеринары ===
class VetListView(LoginRequiredMixin, ListView):
    template_name = 'clinics/vet_list.html'
    context_object_name = 'vets'

    def get_queryset(self):
        user = self.request.user
        clinic_ids = Clinic.objects.filter(admins=user).values_list('id', flat=True)
        return User.objects.filter(
            managed_clinics__id__in=clinic_ids,
            user_type__in=['vet', 'clinic_admin']
        ).distinct()


class VetDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'clinics/vet_detail.html'
    context_object_name = 'vet'

    def get_queryset(self):
        user = self.request.user
        clinic_ids = Clinic.objects.filter(admins=user).values_list('id', flat=True)
        return User.objects.filter(
            id=self.kwargs['pk'],
            managed_clinics__id__in=clinic_ids
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vet = self.object
        assignments = ServiceAssignment.objects.filter(vet=vet)
        context['assignments'] = assignments
        return context


class ServiceDetailView(LoginRequiredMixin, DetailView):
    model = Service
    template_name = 'clinics/service_detail.html'
    context_object_name = 'service'

    def dispatch(self, request, *args, **kwargs):
        service = self.get_object()
        if request.user not in service.clinic.admins.all():
            raise PermissionDenied("Доступ запрещён")
        return super().dispatch(request, *args, **kwargs)


# =========================================================================
#  ПУБЛИЧНЫЙ КАТАЛОГ — клиники и врачи (аналог «ПроДокторов» для вет)
# =========================================================================

class PublicClinicListView(ListView):
    model = Clinic
    template_name = 'clinics/clinic_list_public.html'
    context_object_name = 'clinics'
    paginate_by = 12

    def get_queryset(self):
        qs = Clinic.objects.all().prefetch_related('services')
        params = self.request.GET

        q = params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(services__name__icontains=q) |
                Q(vets__specializations__name__icontains=q)
            )

        city = params.get('city', '').strip()
        if city:
            qs = qs.filter(city__iexact=city)

        spec_slug = params.get('spec', '').strip()
        if spec_slug:
            qs = qs.filter(vets__specializations__slug=spec_slug)

        if params.get('online'):
            qs = qs.filter(accepts_online=True)
        if params.get('h24'):
            qs = qs.filter(is_24h=True)
        if params.get('surgery'):
            qs = qs.filter(has_surgery=True)
        if params.get('lab'):
            qs = qs.filter(has_lab=True)

        sort = params.get('sort', 'rating')
        if sort == 'rating':
            qs = qs.order_by('-rating', '-reviews_count', 'name')
        elif sort == 'reviews':
            qs = qs.order_by('-reviews_count', '-rating', 'name')
        else:
            qs = qs.order_by('name')

        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['cities'] = (
            Clinic.objects.exclude(city='')
            .values_list('city', flat=True)
            .distinct()
            .order_by('city')
        )
        ctx['specs'] = Specialization.objects.all()
        ctx['filters'] = self.request.GET
        ctx['selected_city'] = self.request.GET.get('city', '')
        ctx['selected_spec'] = self.request.GET.get('spec', '')
        ctx['q'] = self.request.GET.get('q', '')
        ctx['sort'] = self.request.GET.get('sort', 'rating')
        return ctx


class PublicClinicDetailView(DetailView):
    model = Clinic
    template_name = 'clinics/clinic_detail_public.html'
    context_object_name = 'clinic'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        clinic = self.object
        ctx['vets'] = (
            VetProfile.objects.filter(clinic=clinic, is_published=True)
            .select_related('user')
            .prefetch_related('specializations')
        )
        ctx['services'] = clinic.services.all().order_by('name')
        ctx['reviews'] = (
            Review.objects.filter(clinic=clinic, is_published=True)
            .select_related('author')[:20]
        )
        return ctx


class PublicVetListView(ListView):
    model = VetProfile
    template_name = 'clinics/vet_list_public.html'
    context_object_name = 'vets'
    paginate_by = 16

    def get_queryset(self):
        qs = (
            VetProfile.objects.filter(is_published=True)
            .select_related('user', 'clinic')
            .prefetch_related('specializations')
        )
        params = self.request.GET

        q = params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(specializations__name__icontains=q) |
                Q(clinic__name__icontains=q)
            )

        spec_slug = params.get('spec', '').strip()
        if spec_slug:
            qs = qs.filter(specializations__slug=spec_slug)

        city = params.get('city', '').strip()
        if city:
            qs = qs.filter(clinic__city__iexact=city)

        if params.get('online'):
            qs = qs.filter(accepts_online=True)
        if params.get('house_call'):
            qs = qs.filter(accepts_house_call=True)

        price_max = params.get('price_max')
        if price_max and price_max.isdigit():
            qs = qs.filter(price_consultation__lte=int(price_max))

        sort = params.get('sort', 'rating')
        if sort == 'price':
            qs = qs.order_by('price_consultation', '-rating')
        elif sort == 'experience':
            qs = qs.order_by('-experience_years', '-rating')
        else:
            qs = qs.order_by('-rating', '-reviews_count')

        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['specs'] = Specialization.objects.all()
        ctx['cities'] = (
            Clinic.objects.exclude(city='')
            .values_list('city', flat=True)
            .distinct()
            .order_by('city')
        )
        ctx['filters'] = self.request.GET
        ctx['selected_spec'] = self.request.GET.get('spec', '')
        ctx['selected_city'] = self.request.GET.get('city', '')
        ctx['q'] = self.request.GET.get('q', '')
        ctx['sort'] = self.request.GET.get('sort', 'rating')
        return ctx


class PublicVetDetailView(DetailView):
    model = VetProfile
    template_name = 'clinics/vet_detail_public.html'
    context_object_name = 'vet'

    def get_queryset(self):
        return (
            VetProfile.objects.filter(is_published=True)
            .select_related('user', 'clinic')
            .prefetch_related('specializations')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        vet = self.object
        ctx['services'] = (
            Service.objects.filter(clinic=vet.clinic).order_by('name')
            if vet.clinic_id else []
        )
        ctx['reviews'] = (
            Review.objects.filter(vet=vet, is_published=True)
            .select_related('author')[:20]
        )
        return ctx