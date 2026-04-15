# clinics/urls.py
from django.urls import path
from . import views

app_name = 'clinics'

urlpatterns = [
    # ... существующие маршруты
    path('', views.ClinicListView.as_view(), name='clinic_list'),
    path('add/', views.ClinicCreateView.as_view(), name='clinic_add'),  # ← добавьте эту строку
    path('<int:pk>/', views.ClinicDetailView.as_view(), name='clinic_detail'),
    path('public/', views.PublicClinicListView.as_view(), name='clinic_list_public'),
    path('register/', views.ClinicRegisterView.as_view(), name='clinic_register'),
    
    # Маршруты для дашборда и ветеринаров
    path('dashboard/', views.ClinicDashboardView.as_view(), name='dashboard'),
    path('vets/', views.VetListView.as_view(), name='vet_list'),
    path('vet/<int:pk>/', views.VetDetailView.as_view(), name='vet_detail'),
    
    # Маршруты для услуг (если они остались здесь, а не в services/)
    path('services/', views.ServiceListView.as_view(), name='service_list'),
    path('services/create/', views.ServiceCreateView.as_view(), name='service_create'),
    path('services/<int:pk>/edit/', views.ServiceUpdateView.as_view(), name='service_edit'),
    
    # clinics
    path('public/', views.PublicClinicListView.as_view(), name='clinic_list_public'),
    path('public/<int:pk>/', views.PublicClinicDetailView.as_view(), name='clinic_detail_public'),
]