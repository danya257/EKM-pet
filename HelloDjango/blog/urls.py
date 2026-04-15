# blog/urls.py
from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.BlogHomeView.as_view(), name='home'),
    path('article/<slug:slug>/', views.ArticleDetailView.as_view(), name='article_detail'),
    path('create/', views.article_create_view, name='article_create'),  # ← новое
]