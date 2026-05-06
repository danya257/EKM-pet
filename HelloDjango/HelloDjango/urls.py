# vetmis/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

from core.views import landing_view

urlpatterns = [
    path('', landing_view, name='landing'),  # главная — лендинг с живыми числами
    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls')),
    path('pets/', include('pets.urls')),
    path('clinics/', include('clinics.urls')),
    path('records/', include('medical_records.urls')),
    path('api/', include('api.urls')),
    path('core/', include('core.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('about/', TemplateView.as_view(template_name='core/about.html'), name='about'),
    path('privacy/', TemplateView.as_view(template_name='core/privacy.html'), name='privacy'),
    path('blog/', include('blog.urls')),
    path('chat/', include('chat.urls')),
    path('services/', include('services.urls')),
]

handler400 = 'django.views.defaults.bad_request'
handler403 = 'django.views.defaults.permission_denied'
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # На продакшене (Beget) всегда добавляем маршруты для медиа
    # так как файлы будут в public_html/media и доступны через Nginx
    from django.views.static import serve
    urlpatterns += [
        path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    ]