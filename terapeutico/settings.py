import os
from decouple import config

from pathlib import Path

DEBUG = True

ALLOWED_HOSTS = ['*']

DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: v.split(','))

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-an0av%#p4%nyhcd2r!3wmxb(g91te_+i&@d^jn3+$nsjr1dn3w'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'upme',
    'usuarios',    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'terapeutico.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
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

WSGI_APPLICATION = 'terapeutico.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'terapeutico', #config('POSTGRES_DB'),
    'USER': 'useradmin', #config('POSTGRES_USER'),
    'PASSWORD': 's3nh@dmin', #config('POSTGRES_PASSWORD'),
    'HOST': '10.16.0.16', # '10.16.0.138',
    'PORT': '5432',  #  5433
    }
       
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True

CSRF_TRUSTED_ORIGINS = ["https://terapeutico.huufma.br"]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Authentication
LOGIN_URL = 'usuarios:login'
LOGOUT_REDIRECT_URL = 'usuarios:login'
LOGIN_REDIRECT_URL = 'usuarios:boas-vindas'

# Configurações do LDAP
AUTH_LDAP_SERVER_URI = "ldap://dc.huufma.br:389"   #"ldap://ad.ebserh.gov.br"  # ou ldaps://ad.ebserh.gov.br:636 para conexão segura
AUTH_LDAP_SEARCH_BASE = "DC=dc,DC=huufma,DC=br"
AUTH_LDAP_DOMAIN = "ebserhnet"  # Domínio do AD
AUTH_LDAP_ADMIN_GROUP = "CN=GrupoDjangoAdmins,OU=Grupos,DC=dc,DC=huufma,DC=br"


# Configurações de sessão
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_SECURE = False  # True em produção com HTTPS
CSRF_COOKIE_SECURE = False    # True em produção com HTTPS

JWT_SECRET_KEY = 'django-insecure-an0av%#p4%nyhcd2r!3wmxb(g91te_+i&@d^jn3+$nsjr1dn3w'
JWT_EXPIRATION_SECONDS = 60  # 1 minuto de validade


AUTH_USER_MODEL = 'usuarios.User'