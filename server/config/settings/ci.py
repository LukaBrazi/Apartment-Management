# CI settings — used in GitHub Actions Docker E2E job
# Inherits from base; no MinIO, no Mailpit, no Celery workers needed.
from .base import *  # noqa: F403
from .base import BASE_DIR, INSTALLED_APPS, env

DEBUG = True
SECRET_KEY = "ci-insecure-key-for-testing-only-do-not-use-in-production"
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:8080"]
SITE_NAME = "Skandi Apartments"


# Caches
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}


# Static / Media — filesystem only (no MinIO)
# ------------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = str(BASE_DIR / "staticfiles")
MEDIA_URL = "/media/"
MEDIA_ROOT = str(BASE_DIR / "media")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

STATICFILES_DIRS = []
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]


# Email — console backend (no Mailpit)
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "ci@sckandi.local"


# Celery — run tasks synchronously (no worker containers)
# ------------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True


# DRF Throttling — disabled in CI to avoid hitting rate limits during tests
# (mirrors the same override in local.py)
# ------------------------------------------------------------------------------
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}


# Django Extensions (for runserver_plus used in start script)
# ------------------------------------------------------------------------------
INSTALLED_APPS += ["django_extensions"]
