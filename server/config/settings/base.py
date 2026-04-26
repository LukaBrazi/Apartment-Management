# Imports
from pathlib import Path

import environ
from celery.schedules import crontab
from django.utils.timezone import timedelta

# Base directory of the Django project
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent


# App directory of the Django project
APPS_DIR = BASE_DIR / "apps"


# Initialize environment variables
env = environ.Env()


# Read the environment variables from the .env file
READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    env.read_env(str(BASE_DIR / ".env"))


# Set the auth user model
AUTH_USER_MODEL = "users.User"


# General
# ------------------------------------------------------------------------------
DEBUG = env.bool("DJANGO_DEBUG", False)
TIME_ZONE = "Europe/Kyiv"
LANGUAGE_CODE = "uk"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("uk", "Українська"),
    ("en", "English"),
]

LOCALE_PATHS = [str(BASE_DIR / "locale")]


# Site settings
# ------------------------------------------------------------------------------
SITE_ID = 1
SITE_NAME = env("SITE_NAME", default="ApartmentOS")
PLATFORM_DOMAINS = env.list("PLATFORM_DOMAINS", default=["estateos.com"])


# Environment tag — single source of truth for "which tier is this?"
# ------------------------------------------------------------------------------
# Overridden in each settings module (local/ci/test/production). The default
# "unknown" is deliberately conservative: if a new settings module forgets to
# set ENVIRONMENT, destructive guards (e.g. seed_demo --reset) treat it as
# unsafe. See apps/common/seed/reset_scope.py for consumers.
ENVIRONMENT = "unknown"

# Demo reset opt-in flag — ``seed_demo --reset`` refuses to run in
# ``ENVIRONMENT == "production"`` unless this is explicitly set to True via
# the ``ALLOW_DEMO_RESET`` env var on the worker. Default False so a fresh
# prod deploy cannot accidentally wipe real tenants on first beat tick.
ALLOW_DEMO_RESET = env.bool("ALLOW_DEMO_RESET", default=False)


# Databases
# ------------------------------------------------------------------------------
DATABASES = {"default": env.db("DATABASE_URL", default="sqlite:///test.db")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Urls
# ------------------------------------------------------------------------------
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"


# Apps
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "storages",
    "django_celery_beat",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_countries",
    "phonenumber_field",
    "djoser",
    "autoslug",
    "taggit",
    "django_filters",
    "djcelery_email",
    "drf_spectacular",
    "drf_spectacular_sidecar",
]
LOCAL_APPS = [
    "apps.users",
    "apps.common",
    "apps.profiles",
    "apps.apartments",
    "apps.issues",
    "apps.reports",
    "apps.ratings",
    "apps.posts",
    "apps.passes",
    "apps.news",
    "apps.site_settings",
    "apps.notifications",
    "apps.organizations",
    "apps.feedback",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# Authentication
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]


# Passwords
# ------------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Middleware
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.OrganizationMiddleware",
]


# Templates
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(APPS_DIR / "templates"), str(APPS_DIR / "static")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# Security
# ------------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"


# Email
# ------------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_TIMEOUT = 5


# Admin
# ------------------------------------------------------------------------------
ADMIN_URL = "django-admin/"
ADMINS = [("Andriienko Dmytro", "dimas130790@gmail.com")]
MANAGERS = ADMINS


# Logging
# ------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}


# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="memory://")
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_BACKEND_ALWAYS_RETRY = True
CELERY_RESULT_BACKEND_MAX_RETRIES = 10
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TIME_LIMIT = 5 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 60
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_BEAT_SCHEDULE = {
    "update-reputations-every-day": {
        "task": "update_all_reputations",
        "schedule": timedelta(days=1),
    },
    # Nightly demo reset. CELERY_TIMEZONE = Europe/Kyiv, so
    # `crontab(hour=23, minute=0)` fires at 23:00 local time every day —
    # DST handled by Celery, no UTC conversion needed.
    #
    # The DatabaseScheduler treats this dict as the initial seed for
    # django_celery_beat's PeriodicTask table; after the first beat run
    # ops can toggle / edit the schedule via Django Admin without a
    # code change. See server/apps/common/tasks.py::seed_demo_reset.
    "seed-demo-reset-nightly": {
        "task": "seed_demo_reset",
        "schedule": crontab(hour=23, minute=0),
    },
}


# Django CORS Headers
# -------------------------------------------------------------------------------
CORS_URLS_REGEX = r"^/api/.*$"


# Taggit Config
# -------------------------------------------------------------------------------
TAGGIT_CASE_INSENSITIVE = True


# Cookies
# -------------------------------------------------------------------------------
COOKIE_NAME = "access"
COOKIE_SAMESITE = "Lax"
COOKIE_PATH = "/"
COOKIE_HTTPONLY = True
COOKIE_SECURE = env.bool("COOKIE_SECURE", default=True)


# Django REST Framework
# -------------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": ("apps.common.cookie_auth.CookieAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "PAGE_SIZE": 10,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "200/day",
        "user": "500/day",
        "login": "5/minute",
        "password_reset": "3/hour",
    },
}


# DRF Spectacular Config
# -------------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": f"{env('SITE_NAME', default='ApartmentOS')} API",
    "DESCRIPTION": "Residential complex management platform API. Tenants can report issues, request vehicle passes, view news and announcements. Built with Django REST Framework.",
    "VERSION": "1.0.0",
    "CONTACT": {"name": "Andriienko Dmytro", "email": "d.andriienko@propmanager.local"},
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
}


# Django Simple JWT
# -------------------------------------------------------------------------------
# ``SIGNING_KEY`` is intentionally read lazily via ``LazySettings`` — each tier
# defines ``SECRET_KEY`` (local/test/ci have explicit dev keys; production uses
# ``env("DJANGO_SECRET_KEY")`` *without* a default, so a missing env var fails
# the boot loud).  Reusing ``SECRET_KEY`` here removes the previous insecure
# fallback ``"test-signing-key-change-in-production"`` that would silently sign
# JWTs with a public placeholder if the env var was unset.
SIMPLE_JWT = {
    # Resolved at import-time via LazyObject — Django's settings system fills
    # this in after each tier-specific module sets SECRET_KEY.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Remember Me
# -------------------------------------------------------------------------------
# When a user ticks "Запам'ятати мене" on the login form, the refresh
# token's `exp` claim and the refresh/logged_in cookie Max-Age are
# extended to this lifetime. Without remember-me, tokens use the stock
# SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] and cookies are session-only
# (Max-Age omitted → browser drops them on close).
#
# The extension is driven by a `remember: true` claim baked into the
# refresh JWT itself — so it survives rotation without a separate
# server-side marker that could desync.
REMEMBER_ME_REFRESH_LIFETIME = timedelta(days=14)

# Telegram — PR-14 multi-tenant bots
# -------------------------------------------------------------------------------
# Bot tokens are Fernet-encrypted at rest (see apps/notifications/encryption.py
# and docs/ADR-014-multi-tenant-telegram-bots.md).  Generate a key once per
# environment:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# and set TELEGRAM_BOT_ENCRYPTION_KEY in the env store.  Losing the key means
# every stored token goes unreadable and has to be re-entered by super_admin.
#
# For key rotation, set TELEGRAM_BOT_ENCRYPTION_KEYS (comma-separated, newest
# first).  Reads try each in turn; writes always use the first.  Runbook:
# docs/TELEGRAM_BOT_SETUP.md.
TELEGRAM_BOT_ENCRYPTION_KEY = env("TELEGRAM_BOT_ENCRYPTION_KEY", default="")
TELEGRAM_BOT_ENCRYPTION_KEYS = env.list("TELEGRAM_BOT_ENCRYPTION_KEYS", default=[])

# Public origin used by the setup_telegram_webhooks management command when it
# calls Telegram's setWebhook(url=...).  Leave empty in dev — polling path
# (manage.py run_bot --org-slug=...) doesn't need it.
PLATFORM_PUBLIC_URL = env("PLATFORM_PUBLIC_URL", default="")


# Djoser Config
# -------------------------------------------------------------------------------
DJOSER = {
    "USER_ID_FIELD": "id",
    "LOGIN_FIELD": "email",
    "TOKEN_MODEL": None,
    "PASSWORD_CHANGED_EMAIL_CONFIRMATION": True,
    "PASSWORD_RESET_CONFIRM_RETYPE": True,
    "PASSWORD_RESET_CONFIRM_URL": "password-reset/{uid}/{token}/",
    "SERIALIZERS": {
        "current_user": "apps.users.serializers.CustomUserSerializer",
    },
}

