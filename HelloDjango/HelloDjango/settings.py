"""
Django settings for vetmis project.
Adapted for Beget hosting.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# SECURITY SETTINGS (PRODUCTION)
# =============================================================================

# ⚠️ ВНИМАНИЕ: Сгенерируйте новый ключ! 
# Старый ключ скомпрометирован, так как был показан в чате.
# Команда для генерации: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-CHANGE-THIS-KEY-IN-PRODUCTION-please-generate-new-one')

# На продакшене отключаем отладку
DEBUG = True

# Разрешенные хосты - добавьте сюда все ваши домены
ALLOWED_HOSTS = [
    'kimdanrf.beget.tech',
    'www.kimdanrf.beget.tech',
    'localhost',
    '127.0.0.1',
    # Если будет свой домен:
    # 'ваш-домен.ru',
    # 'www.ваш-домен.ru',
]

# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'whitenoise.runserver_nostatic',  # Можно оставить, не мешает
    'rest_framework',
    'rest_framework.authtoken', 
    'drf_spectacular',
    
    # Local apps
    'users',
    'api',
    'pets',
    'clinics',
    'medical_records',
    'core',
    'blog',
    'chat',
    'services',
    # 'vetmis',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Whitenoise для статики
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'HelloDjango.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'HelloDjango.passenger_wsgi.application'

# =============================================================================
# DATABASE SETTINGS (Beget MySQL)
# =============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'kimdanrf_dj1',           # Имя БД из панели Beget
        'USER': 'kimdanrf_dj1',           # Пользователь БД из панели Beget
        'PASSWORD': 'u7BtyOUi',          # Пароль от БД из панели Beget
        'HOST': 'localhost',              # На Beget MySQL всегда на localhost
        'PORT': '3306',                   # Стандартный порт MySQL
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',         # Поддержка эмодзи и кириллицы
        },
        'CONN_MAX_AGE': 600, 
        'CONN_HEALTH_CHECKS': True,# Keep-alive соединение (опционально)
    }
}

# =============================================================================
# REST FRAMEWORK SETTINGS
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema', 
}

# =============================================================================
# AUTH & USER SETTINGS
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Кастомная модель пользователя
AUTH_USER_MODEL = 'users.User'

# Редиректы после входа/выхода
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login/'

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC & MEDIA FILES (Beget Configuration)
# =============================================================================

STATIC_URL = '/static/'

# Путь, куда Django соберет статику командой `collectstatic`
STATIC_ROOT = '/home/k/kimdanrf/kimdanrf.beget.tech/public_html/static'

# Альтернативный вариант (если хотите в public_html):
# STATIC_ROOT = '/home/k/kimdanrf/kimdanrf.beget.tech/public_html/static/'

# Настройка для Whitenoise (сжатие статики)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Медиа-файлы (загруженные пользователями)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# Для раздачи медиа на продакшене лучше настроить Nginx в панели Beget,
# но для начала можно оставить так.

# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# LOGGING (Опционально, но полезно для отладки на продакшене)
# =============================================================================
# dj_database_url.parse(os.environ['DATABASE_URL'], conn_max_age=600, conn_health_checks=True)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'django_errors.log'),
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'ERROR',
    },
}