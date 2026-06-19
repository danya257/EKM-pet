from django.urls import path

from . import views

app_name = 'appointments'

urlpatterns = [
    path('', views.AppointmentListView.as_view(), name='list'),
    path('to/<int:vet_pk>/', views.create_appointment, name='create'),
    path('<int:pk>/', views.AppointmentDetailView.as_view(), name='detail'),
]
