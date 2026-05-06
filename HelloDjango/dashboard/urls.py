# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.analytics_dashboard, name='index'),
    path('analytics/', views.analytics_dashboard, name='analytics'),
    path('api/data/', views.analytics_api, name='api_data'),
    path('export/csv/', views.export_csv, name='export_csv'),
]
