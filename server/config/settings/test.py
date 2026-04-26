"""Test settings — uses SQLite, no external services required."""
from .base import *  # noqa: F403
from .base import INSTALLED_APPS

SECRET_KEY = "test-secret-key-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]
SITE_NAME = "ApartmentOS Test"

# Environment tag — see base.py and apps/common/seed/reset_scope.py.
ENVIRONMENT = "test"
# Test DB is rebuilt every run, so --reset is inherently safe. Tests that
# want to exercise the prod-refusal path override ENVIRONMENT explicitly
# via ``override_settings``.
ALLOW_DEMO_RESET = True

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

# Telegram — use a deterministic Fernet key so encrypt/decrypt round-trips
# work in tests without env setup. Never use this key outside of tests —
# it is intentionally committed and therefore public.
TELEGRAM_BOT_ENCRYPTION_KEY = "DxcpeackQHQYgMpYryJJ-pZ4hQPQs278MjbovLLRuKE="
# Test-only placeholder origin used by webhook URL builders.
PLATFORM_PUBLIC_URL = "https://test.apartmentos.local"

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

# Disable throttling in tests — LocMemCache persists between test methods,
# and login throttle (5/min) triggers 429 on repeated auth test calls.
#
# We zero out DEFAULT_THROTTLE_CLASSES so the global anon/user throttles
# never bite, BUT we still keep the per-scope rates populated.  Why:
# views can pin ``throttle_classes = [ScopedRateThrottle]`` directly on
# the class body (PR-8 burst caps on issue/pass/post/rating creates),
# and DRF's ``ScopedRateThrottle.allow_request`` resolves the rate from
# ``THROTTLE_RATES`` regardless of what DEFAULT_THROTTLE_CLASSES says.
# An empty rates dict raises ``ImproperlyConfigured: No default throttle
# rate set for 'issue_create' scope`` in every issue-create test.
#
# Setting absurdly high values keeps the scope wired but practically
# unreachable in any single test (the per-scope throttle tests in
# test_burst_throttles.py override these explicitly).
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10000/day",
        "user": "10000/day",
        "login": "10000/day",
        "password_reset": "10000/day",
        "issue_create": "10000/hour",
        "pass_create": "10000/hour",
        "post_create": "10000/hour",
        "rating_create": "10000/hour",
    },
}
