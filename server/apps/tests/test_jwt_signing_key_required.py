"""Регресія: JWT SIGNING_KEY не повинен мати fallback default — fail fast.

PR-1 (fix/critical-security): SIMPLE_JWT["SIGNING_KEY"] мав небезпечний
default ``"test-signing-key-change-in-production"``. Це означало, що якщо
``DJANGO_SECRET_KEY`` env-var не заданий у production, JWT'и підписувалися
відомим публічним ключем — будь-хто міг видати валідний access token.

Тепер SIMPLE_JWT не задає власний SIGNING_KEY — `simplejwt` за замовчуванням
використовує ``settings.SECRET_KEY`` (див.
``rest_framework_simplejwt/settings.py:20``). У production
``SECRET_KEY = env("DJANGO_SECRET_KEY")`` без default — невказана env-var
вибиває з ``ImproperlyConfigured`` при бутстрапі.
"""

from django.conf import settings as dj_settings
from rest_framework_simplejwt.settings import api_settings as jwt_api_settings


def test_jwt_simple_settings_does_not_override_signing_key():
    """``SIMPLE_JWT`` dict не повинен містити ключ ``SIGNING_KEY`` —
    simplejwt підставляє ``settings.SECRET_KEY`` як default.
    """
    assert "SIGNING_KEY" not in dj_settings.SIMPLE_JWT, (
        "SIMPLE_JWT['SIGNING_KEY'] is set explicitly. PR-1 removed the "
        "insecure fallback; let simplejwt fall back to settings.SECRET_KEY "
        "so production fails fast when DJANGO_SECRET_KEY env is missing."
    )


def test_resolved_signing_key_matches_secret_key():
    """Effective signing key (resolved via simplejwt's lazy api_settings) must
    equal the project-wide ``SECRET_KEY``. This is the single-source-of-truth
    contract: rotate ``DJANGO_SECRET_KEY`` once, and every JWT issuer/verifier
    follows.
    """
    assert jwt_api_settings.SIGNING_KEY == dj_settings.SECRET_KEY


def test_resolved_signing_key_is_not_legacy_placeholder():
    """Хардкоджена строка-плейсхолдер не повинна потрапити у будь-який tier."""
    assert (
        jwt_api_settings.SIGNING_KEY != "test-signing-key-change-in-production"
    ), (
        "Effective JWT signing key still equals the legacy "
        "'test-signing-key-change-in-production' placeholder — remove the "
        "default and let production fail fast on a missing DJANGO_SECRET_KEY."
    )
