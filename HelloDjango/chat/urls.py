# chat/urls.py
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_list_view, name='chat_list'),
    path('<int:chat_id>/', views.chat_detail_view, name='chat_detail'),
    path('start/<int:clinic_id>/<int:vet_id>/', views.start_chat_view, name='start_chat'),
]