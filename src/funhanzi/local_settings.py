from .settings import *

# Override the database settings to use SQLite for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR.parent / 'db.sqlite3',
    }
}

SECRET_KEY = 'django-insecure-this-is-a-very-secret-key-for-local-development-only'
