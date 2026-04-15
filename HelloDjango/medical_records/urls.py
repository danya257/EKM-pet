# medical_records/urls.py
from django.urls import path
from . import views

app_name = 'medical_records'

urlpatterns = [
    path('pet/<int:pet_pk>/add/', views.MedicalRecordCreateView.as_view(), name='record_add'),
    path('<int:pk>/', views.MedicalRecordDetailView.as_view(), name='record_detail'),
]