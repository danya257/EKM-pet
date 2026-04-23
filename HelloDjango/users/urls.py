# users/urls.py
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/',          views.CustomLoginView.as_view(),   name='login'),
    path('login/owner/',    views.OwnerLoginView.as_view(),    name='login_owner'),
    path('login/clinic/',   views.ClinicLoginView.as_view(),   name='login_clinic'),
    path('logout/',         views.CustomLogoutView.as_view(),  name='logout'),
    path('register/',       views.RegisterView.as_view(),      name='register'),
    path('profile/',        views.profile_view,                name='profile'),

    # PIN
    path('pin/login/',      views.pin_login_view,              name='pin_login'),
    path('pin/setup/',      views.pin_setup_view,              name='pin_setup'),
    path('pin/disable/',    views.pin_disable_view,            name='pin_disable'),
]
