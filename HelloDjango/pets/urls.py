from django.urls import path
from . import views

app_name = 'pets'

urlpatterns = [
    path('', views.PetListView.as_view(), name='pet_list'),
    path('add/', views.PetCreateView.as_view(), name='pet_add'),
    path('<int:pk>/', views.PetDetailView.as_view(), name='pet_detail'),
    path('<int:pk>/edit/', views.PetUpdateView.as_view(), name='pet_edit'),
    path('qr/<uuid:uuid>/', views.pet_qr_view, name='pet_qr_view'),
    path('qr/<uuid:uuid>/download/', views.pet_qr_download, name='pet_qr_download'),
]