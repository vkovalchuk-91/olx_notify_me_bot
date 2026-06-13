import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
    USE_ASYNC_MODE=(bool, False),
    WORKERS_NUMBER=(int, 4),
    REQUEST_INTERVAL_MINUTES=(int, 15),
    INITIAL_REQUEST_DELAY_SECONDS=(int, 30),
    INSTA_REQUEST_INTERVAL_MINUTES=(int, 30),
    USE_SQLITE=(bool, True),
    WEB_REGISTRATION_CODE_TTL_MINUTES=(int, 15),
)

environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', 'web'])


def sqlite_db_path(name: str) -> Path:
    path = Path(name)
    if path.is_absolute():
        return path
    return BASE_DIR / path

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'apps.telegram_users',
    'apps.monitors',
    'apps.insta_monitor',
    'apps.audit_logs',
    'apps.api',
    'apps.web',
    'apps.telegram_bot',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

if env('USE_SQLITE'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': sqlite_db_path(env('LOCAL_DB_NAME', default='django_olx_notify.db')),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': env('DB_HOST'),
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'PORT': env('DB_PORT', default='5432'),
            'CONN_MAX_AGE': env.int('DB_CONN_MAX_AGE', default=0),
            'OPTIONS': {
                'connect_timeout': env.int('DB_CONNECT_TIMEOUT', default=10),
            },
        }
    }

DATABASES['logs'] = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': sqlite_db_path(env('LOG_DB_NAME', default='job_logs.sqlite3')),
    'OPTIONS': {
        'timeout': env.int('LOG_DB_TIMEOUT', default=20),
    },
}

DATABASE_ROUTERS = ['config.db_routers.AuditLogsRouter']

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
AUTHENTICATION_BACKENDS = ['apps.web.auth_backends.CaseInsensitiveUsernameBackend']

LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'web:login'
LOGIN_REDIRECT_URL = 'web:dashboard'
LOGOUT_REDIRECT_URL = 'web:login'
WEB_REGISTRATION_CODE_TTL_MINUTES = env('WEB_REGISTRATION_CODE_TTL_MINUTES')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# Telegram
TELEGRAM_TOKEN = env('TELEGRAM_TOKEN', default='')
TELEGRAM_BOT_USERNAME = env('TELEGRAM_BOT_USERNAME', default='')
WEB_REGISTRATION_BASE_URL = env('WEB_REGISTRATION_BASE_URL', default='http://127.0.0.1:8000')

# Scrapers
USE_ASYNC_MODE = env('USE_ASYNC_MODE')
WORKERS_NUMBER = env('WORKERS_NUMBER')
REQUEST_INTERVAL_MINUTES = env('REQUEST_INTERVAL_MINUTES')
INSTA_REQUEST_INTERVAL_MINUTES = env('INSTA_REQUEST_INTERVAL_MINUTES')

# Celery
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    'check-new-ads': {
        'task': 'apps.monitors.tasks.check_new_ads_task',
        'schedule': REQUEST_INTERVAL_MINUTES * 60,
    },
    'check-new-insta-content': {
        'task': 'apps.insta_monitor.tasks.check_new_insta_content_task',
        'schedule': INSTA_REQUEST_INTERVAL_MINUTES * 60,
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'db': {
            'class': 'apps.audit_logs.logging_handler.DatabaseLogHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'db'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'db'],
            'level': 'INFO',
            'propagate': False,
        },
        'aiogram': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
