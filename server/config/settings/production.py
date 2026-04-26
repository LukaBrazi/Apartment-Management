from .base import *  # noqa: F403
from .base import env

# General
# ------------------------------------------------------------------------------
DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# Environment tag — see base.py and apps/common/seed/reset_scope.py.
# Production is the one tier where seed_demo --reset requires the explicit
# ALLOW_DEMO_RESET env opt-in; ENVIRONMENT=="production" is what flips the
# guard on.
ENVIRONMENT = "production"

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

# Database — Railway provides DATABASE_URL automatically
# ------------------------------------------------------------------------------
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = 60

# Cache — Railway provides REDIS_URL automatically
# ------------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# Celery — uses same Redis
# ------------------------------------------------------------------------------
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Security
# ------------------------------------------------------------------------------
SECURE_SSL_REDIRECT = True
# Railway's internal healthcheck probe hits the container directly via
# plain HTTP (no X-Forwarded-Proto: https header). Without an exempt,
# Django's SecurityMiddleware would respond with a 301 to https:// and
# Railway would mark the deploy as "service unavailable" (non-2xx).
# Exempt the health endpoint so the probe gets 200/503 from our view.
# Note: the value is a list of UNANCHORED REGEX patterns matched against
# the path WITHOUT the leading slash.
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/?$"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# CORS — allow Vercel frontend
# ------------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

# Telegram — PR-14 multi-tenant bots
# ------------------------------------------------------------------------------
# Both of these are REQUIRED on prod. No defaults — a missing key fails the
# worker boot loud instead of silently breaking encryption / webhook setup.
TELEGRAM_BOT_ENCRYPTION_KEY = env("TELEGRAM_BOT_ENCRYPTION_KEY")
PLATFORM_PUBLIC_URL = env("PLATFORM_PUBLIC_URL", default="https://apartmentos.org")

# Storage — Cloudflare R2 (S3-compatible)
# ------------------------------------------------------------------------------
R2_BUCKET_NAME = env("R2_BUCKET_NAME")
R2_ENDPOINT_URL = env("R2_ENDPOINT_URL")  # https://<ACCOUNT_ID>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID = env("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = env("R2_SECRET_ACCESS_KEY")
R2_PUBLIC_URL = env("R2_PUBLIC_URL")  # https://pub-<hash>.r2.dev or custom domain

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": R2_BUCKET_NAME,
            "endpoint_url": R2_ENDPOINT_URL,
            "access_key": R2_ACCESS_KEY_ID,
            "secret_key": R2_SECRET_ACCESS_KEY,
            "region_name": "auto",
            "location": "media",
            "file_overwrite": False,
            "querystring_auth": False,
            "custom_domain": R2_PUBLIC_URL.replace("https://", ""),
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": R2_BUCKET_NAME,
            "endpoint_url": R2_ENDPOINT_URL,
            "access_key": R2_ACCESS_KEY_ID,
            "secret_key": R2_SECRET_ACCESS_KEY,
            "region_name": "auto",
            "location": "static",
            "file_overwrite": True,
            "querystring_auth": False,
            "custom_domain": R2_PUBLIC_URL.replace("https://", ""),
        },
    },
}

STATIC_URL = f"{R2_PUBLIC_URL}/static/"
MEDIA_URL = f"{R2_PUBLIC_URL}/media/"

STATICFILES_DIRS = []
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Email — configure your SMTP provider (SendGrid, Resend, etc.)
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "djcelery_email.backends.CeleryEmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@apartmentos.org")
