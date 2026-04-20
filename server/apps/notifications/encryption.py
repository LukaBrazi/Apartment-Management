"""Symmetric encryption for Telegram bot tokens at rest.

PR-14 stores a Telegram bot token per organization. The token is the
root credential for that bot — anyone holding it can read every chat
the bot is in and DM every user who /start'd it. Storing it plaintext
in Postgres would mean a DB dump leaks every tenant's bot.

We use Fernet (AES-128-CBC + HMAC-SHA256) from ``cryptography``, which
is already an indirect dep. Rationale: well-audited, authenticated,
versioned, and the API surface is two functions (``encrypt`` /
``decrypt``) — so we don't need a Django-layer field lib
(django-cryptography has compat issues with Django 4.2+).

Key source
----------
``settings.TELEGRAM_BOT_ENCRYPTION_KEY`` — 32 URL-safe base64 bytes as
produced by ``Fernet.generate_key()``. Generate once per environment
and keep in the secret store (Railway env, Vault, etc.).

Key rotation
------------
To rotate, populate ``TELEGRAM_BOT_ENCRYPTION_KEYS`` (comma-separated,
newest first). Reads try each key until one works; writes always use
the first. Re-encrypt-in-place happens on the next save(). Rotation
runbook lives in ``docs/TELEGRAM_BOT_SETUP.md``.
"""
from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


def _load_fernet() -> MultiFernet:
    """Build a ``MultiFernet`` from the configured keys.

    Accepts either:
    - ``settings.TELEGRAM_BOT_ENCRYPTION_KEYS`` — list of keys (rotation mode)
    - ``settings.TELEGRAM_BOT_ENCRYPTION_KEY`` — single key (common case)

    Raises ``ImproperlyConfigured`` if neither is set. We fail loud:
    silently falling back to plaintext or a hardcoded dev key would
    undermine the whole point of this module.
    """
    keys = getattr(settings, "TELEGRAM_BOT_ENCRYPTION_KEYS", None)
    if not keys:
        single = getattr(settings, "TELEGRAM_BOT_ENCRYPTION_KEY", None)
        if not single:
            raise ImproperlyConfigured(
                "TELEGRAM_BOT_ENCRYPTION_KEY is not set. Generate one with "
                "`python -c 'from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())'` and set it in the "
                "environment. Never commit the key or reuse across tiers."
            )
        keys = [single]

    fernets: list[Fernet] = []
    for key in keys:
        if isinstance(key, str):
            key = key.encode("ascii")
        try:
            fernets.append(Fernet(key))
        except Exception as exc:  # noqa: BLE001 — re-raise with context
            raise ImproperlyConfigured(
                f"Invalid Telegram bot encryption key (must be 32 url-safe "
                f"base64 bytes produced by Fernet.generate_key()): {exc}"
            ) from exc
    return MultiFernet(fernets)


def encrypt_token(plaintext: str) -> str:
    """Encrypt a bot token. Returns ASCII ciphertext suitable for a TextField."""
    if not plaintext:
        return ""
    fernet = _load_fernet()
    return fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a bot token. Returns empty string for empty input.

    Raises ``InvalidToken`` if the ciphertext is corrupt or the key no
    longer knows how to decrypt it. Callers (e.g. ``send_message_async``)
    should catch this and treat the bot as unusable rather than crash
    the whole task.
    """
    if not ciphertext:
        return ""
    fernet = _load_fernet()
    try:
        return fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.error(
            "Failed to decrypt Telegram bot token — key rotation gap or "
            "tampered ciphertext. Re-set the token via admin.",
        )
        raise


def mask_token(plaintext: str) -> str:
    """Produce a safe-to-display preview of a bot token for UIs.

    Telegram tokens look like ``123456789:AAE...XYZ``. We keep the bot
    ID (digits before the colon) visible and mask the secret body,
    leaving the last 4 chars for human verification ("did I paste the
    right one?").
    """
    if not plaintext:
        return ""
    if ":" in plaintext:
        bot_id, _, secret = plaintext.partition(":")
        tail = secret[-4:] if len(secret) > 4 else "…"
        return f"{bot_id}:••••••••{tail}"
    # Non-standard shape — mask everything but the last 4.
    return f"••••{plaintext[-4:]}" if len(plaintext) > 4 else "••••"
