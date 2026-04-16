"""Test settings — uses SQLite, no external services required."""
from .base import *  # noqa: F403
from .base import INSTALLED_APPS

SECRET_KEY = "test-secret-key-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]
SITE_NAME = "EstateOS Test"

# SQLite for fast tests — no Postgres needed
import os
_TEST_DB = os.environ.get("TEST_DB_PATH", ":memory:")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _TEST_DB,
        "ATOMIC_REQUESTS": True,
    }
}

# Disable password hashing for speed
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# No real email
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "test@alpaapartments.test"

# No Celery, run tasks eagerly/synchronously
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# No MinIO/S3 — use local filesystem
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MEDIA_ROOT = "/tmp/alpha_test_media"
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

# Remove storage-related third-party apps not needed in tests
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in ("storages",)]
