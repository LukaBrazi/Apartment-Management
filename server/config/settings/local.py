# Imports
from .base import *  # noqa: F403
from .base import BASE_DIR, INSTALLED_APPS, env

# General
# ------------------------------------------------------------------------------
DEBUG = True
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="QTMT8ZsZaDOSmVFhCTmJULzMu1DLNxbqoKKAGBsFwUwQKRjIzXYyeKCeRRqvGn23",
)
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1", "estateos.serveo.net"]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8080",
    "http://0.0.0.0:8080",
    "http://127.0.0.1:8080",
]
SITE_NAME = "ApartmentOS"


# Caches
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": BASE_DIR / ".cache",
    },
}


# MinIO settings
# ------------------------------------------------------------------------------
MINIO_STORAGE_ENDPOINT = env("MINIO_STORAGE_ENDPOINT")
MINIO_STORAGE_ACCESS_KEY = env("MINIO_STORAGE_ACCESS_KEY")
MINIO_STORAGE_SECRET_KEY = env("MINIO_STORAGE_SECRET_KEY")
MINIO_STORAGE_USE_HTTPS = False


# AWS S3 settings (assuming MinIO setup)
# ------------------------------------------------------------------------------
AWS_S3_ENDPOINT_URL = f"http://{MINIO_STORAGE_ENDPOINT}"
AWS_ACCESS_KEY_ID = MINIO_STORAGE_ACCESS_KEY
AWS_SECRET_ACCESS_KEY = MINIO_STORAGE_SECRET_KEY
AWS_STORAGE_BUCKET_NAME = "skandi-apartments"
AWS_S3_REGION_NAME = "us-east-1"
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_DEFAULT_ACL = "private"
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = True
AWS_S3_CUSTOM_DOMAIN = f"localhost:8080/minio/storage/{AWS_STORAGE_BUCKET_NAME}"


# Static files settings
# ------------------------------------------------------------------------------
STATIC_URL = f"http://localhost:8080/minio/storage/{AWS_STORAGE_BUCKET_NAME}/static/"

# Media files settings
# ------------------------------------------------------------------------------
MEDIA_URL = f"http://localhost:8080/minio/storage/{AWS_STORAGE_BUCKET_NAME}/media/"

STORAGES = {
    "default": {"BACKEND": "config.settings.storage_backends.MediaStorage"},
    "staticfiles": {"BACKEND": "config.settings.storage_backends.StaticStorage"},
}


# Static files finders and directories
# ------------------------------------------------------------------------------
STATICFILES_DIRS = []
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]


# Email — use console backend in local dev so activation emails don't fail
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@estateos.local"

# Djoser — skip activation email requirement in local dev
DJOSER = {
    **globals().get("DJOSER", {}),
    "SEND_ACTIVATION_EMAIL": False,
    "SEND_CONFIRMATION_EMAIL": False,
}


# Django Extensions
# ------------------------------------------------------------------------------
INSTALLED_APPS += ["django_extensions"]


# DRF Throttling — disabled in local dev to avoid hitting daily limits
# ------------------------------------------------------------------------------
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}


# Celery
# ------------------------------------------------------------------------------
CELERY_TASK_EAGER_PROPAGATES = True
