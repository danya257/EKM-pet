# clinics/urls.py
from django.urls import path
from . import views

app_name = 'clinics'

urlpatterns = [
    # === Публичный каталог (ПроДокторов-аналог) ===
    path('public/',                 views.PublicClinicListView.as_view(),   name='public_clinic_list'),
    path('public/<int:pk>/',        views.PublicClinicDetailView.as_view(), name='public_clinic_detail'),
    path('vets/public/',            views.PublicVetListView.as_view(),      name='public_vet_list'),
    path('vets/public/<int:pk>/',   views.PublicVetDetailView.as_view(),    name='public_vet_detail'),

    # Алиасы старых имён, чтобы не сломать существующие {% url %}.
    path('public-old/',             views.PublicClinicListView.as_view(),   name='clinic_list_public'),
    path('public-old/<int:pk>/',    views.PublicClinicDetailView.as_view(), name='clinic_detail_public'),

    # === Личный кабинет клиники ===
    path('',                        views.ClinicListView.as_view(),         name='clinic_list'),
    path('add/',                    views.ClinicCreateView.as_view(),       name='clinic_add'),
    path('<int:pk>/',               views.ClinicDetailView.as_view(),       name='clinic_detail'),
    path('dashboard/',              views.ClinicDashboardView.as_view(),    name='dashboard'),

    # === Внутренние врачи / услуги ===
    path('vets/',                   views.VetListView.as_view(),            name='vet_list'),
    path('vet/<int:pk>/',           views.VetDetailView.as_view(),          name='vet_detail'),
    path('services/',               views.ServiceListView.as_view(),        name='service_list'),
    path('services/create/',        views.ServiceCreateView.as_view(),      name='service_create'),
    path('services/<int:pk>/edit/', views.ServiceUpdateView.as_view(),      name='service_edit'),
]
