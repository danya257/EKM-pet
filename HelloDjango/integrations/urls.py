from django.urls import include, path

from . import views

app_name = 'integrations'

urlpatterns = [
    # OAuth 2.0 — выдача/проверка токенов (django-oauth-toolkit endpoints)
    path('oauth/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    # Outbound REST API для МИС
    path('api/appointments/',           views.api_appointments_list, name='api_appointments_list'),
    path('api/appointments/<int:pk>/',  views.api_appointment_detail, name='api_appointment_detail'),
    path('api/services/',               views.api_services_list,     name='api_services_list'),
    path('api/services/sync/',          views.api_services_sync,     name='api_services_sync'),
    path('api/visits/',                 views.api_visit_create,      name='api_visit_create'),

    # Inbound webhook
    path('webhook/<int:integration_id>/', views.webhook_in, name='webhook_in'),
]
