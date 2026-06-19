from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    path('add/<str:target_kind>/<int:pk>/', views.add_review, name='add'),
]
