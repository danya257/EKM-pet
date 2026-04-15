# users/urls.py
from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'users'

urlpatterns = [
    path('login/owner/', views.OwnerLoginView.as_view(), name='login_owner'),
    path('login/clinic/', views.ClinicLoginView.as_view(), name='login_clinic'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.profile_view, name='profile'),
]