"""
Django settings for vetmis project.
Adapted for Beget hosting.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Загрузить .env (рядом с manage.py), если есть. На проде значения
# обычно проставлены через окружение хостинга — но .env работает и там.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

# =============================================================================
# SECURITY SETTINGS (PRODUCTION)
# =============================================================================

# Все секреты — через переменные окружения. См. .env.example
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError(
        'DJANGO_SECRET_KEY не задан. Положите его в .env или окружение.'
    )

DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')

ALLOWED_HOSTS = [
    'kimdanrf.beget.tech',
    'www.kimdanrf.beget.tech',
    'localhost',
    '127.0.0.1',
]

CSRF_TRUSTED_ORIGINS = [
    'https://kimdanrf.beget.tech',
    'https://www.kimdanrf.beget.tech',
]

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'

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
    'dashboard',
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
        'NAME':     os.getenv('DB_NAME', 'kimdanrf_dj1'),
        'USER':     os.getenv('DB_USER', 'kimdanrf_dj1'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST':     os.getenv('DB_HOST', 'localhost'),
        'PORT':     os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
        # Beget MySQL рвёт соединение по wait_timeout — короче чем 600.
        'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '30')),
        'CONN_HEALTH_CHECKS': True,
    }
}

# Используем pymysql как замену mysqlclient
import pymysql
pymysql.install_as_MySQLdb()

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
# На хостинге Beget медиа-файлы должны быть в public_html/media
MEDIA_ROOT = '/home/k/kimdanrf/kimdanrf.beget.tech/public_html/media'

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