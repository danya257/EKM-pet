# api/urls.py
from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('pet/<uuid:uuid>/', views.PetPublicDetailView.as_view(), name='pet-detail'),
    path('records/', views.MedicalRecordListCreateView.as_view(), name='record-list'),
]