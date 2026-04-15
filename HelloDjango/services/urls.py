# services/urls.py
from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('<int:clinic_id>/', views.service_list_view, name='service_list'),
    path('<int:clinic_id>/create/', views.service_create_view, name='service_create'),
    path('<int:clinic_id>/service/<int:service_id>/', views.service_detail_view, name='service_detail'),
    path('<int:clinic_id>/service/<int:service_id>/assign/', views.assignment_create_view, name='assignment_create'),
]