from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import django_heroku
import dj_database_url
import os
import firebase_admin
from firebase_admin import credentials
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

# path_env = os.path.join(BASE_DIR, '.env')
# load_dotenv(path_env)

if not os.path.exists(os.path.join(BASE_DIR, 'antonio-glyzin-storage.json')) \
    and os.environ.get('CERTIFICATE_STORAGE'):
    with open(os.path.join(BASE_DIR, 'antonio-glyzin-storage.json'), 'w') as file:
        file.write(os.environ.get('CERTIFICATE_STORAGE'))
if os.path.exists(os.path.join(BASE_DIR, 'antonio-glyzin-storage.json')):
    FIREBASE_STORAGE = credentials.Certificate(os.path.join(BASE_DIR, 'antonio-glyzin-storage.json'))
    firebase_admin.initialize_app(FIREBASE_STORAGE, {
        'storageBucket': os.environ.get('BUCKET_STORAGE_NAME')
    })
    
if not os.path.exists(BASE_DIR / 'genie.json') \
    and os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
    with open(BASE_DIR / 'genie.json', 'w') as file:
        file.write(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))
        
if os.path.exists(BASE_DIR / 'genie.json'):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(BASE_DIR, 'genie.json')

# os.path.join(BASE_DIR, 'antonio-glyzin-storage.json')
MY_HOST = 'https://puzzle-chats.herokuapp.com'
# MY_HOST = 'http://127.0.0.1:8000'
SITE_ID = 333333333
SECRET_KEY = os.environ.get('SECRET_KEY', get_random_secret_key())
TOKEN_BOT_GLYZIN = os.environ.get('TOKEN_BOT_GLYZIN')
# ME_CHAT_ID = int(os.environ.get('ME_CHAT_ID'))
ME_CHAT_ID = 654579717
DEBUG = False
ALLOWED_HOSTS = ['antonioglyzin.pythonanywhere.com',
                'portfolio-puzzle.web.app',
                'puzzle-chats.herokuapp.com',
                '127.0.0.1']
CORS_ALLOWED_ORIGINS = [
    "https://antonioglyzin.pythonanywhere.com",
    'https://portfolio-puzzle.web.app',
    'https://puzzle-chats.herokuapp.com',
    'http://127.0.0.1'
]

CSRF_TRUSTED_ORIGINS = [
    "https://antonioglyzin.pythonanywhere.com",
    'https://puzzle-chats.herokuapp.com',
    'https://portfolio-puzzle.web.app'
]
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'beatserver',
    'channels',
    'channels_postgres',
    'corsheaders',
    'captcha',
    'rest_framework_simplejwt',
    'easy_thumbnails',
    'martor',
    'chat.apps.ChatConfig',
    'portfolio.apps.PortfolioConfig',
    'base.apps.AuthConfig',
    'genie.apps.GenieConfig'
]
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=15)
}
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bagchat.urls'
ASGI_APPLICATION = "bagchat.asgi.application"
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# WSGI_APPLICATION = 'bagchat.wsgi.application'
TMP_DATABASE_URL='postgres://postgres:postgres@localhost:5432/app'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_postgres.core.PostgresChannelLayer',
        'CONFIG': dj_database_url.parse(os.environ.get('DATABASE_URL', TMP_DATABASE_URL))
    }
}
DATABASES = {
    'default': dj_database_url.parse(os.environ.get('DATABASE_URL', TMP_DATABASE_URL)),
    'channels_postgres': dj_database_url.parse(os.environ.get('DATABASE_URL', TMP_DATABASE_URL))
}
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser'
     ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )
}
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
django_heroku.settings(locals())
DATABASES['default']['CONN_MAX_AGE'] = 0
del DATABASES['default']['OPTIONS']['sslmode']