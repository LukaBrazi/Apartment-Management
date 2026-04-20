"""DRF permissions for the Telegram endpoints.

PR-14 phase 3 replaces the platform-wide ``TELEGRAM_INTERNAL_SECRET``
with per-bot ``internal_secret`` values. Each bot process sends its
own secret and identifies itself via an ``X-Telegram-Bot-Id`` header;
the permission resolves the bot row and compares the secret in
constant time. The resolved bot is stashed on the request as
``request.telegram_bot`` so downstream views don't re-query.
"""
from __future__ import annotations

import hmac

from rest_framework.permissions import BasePermission


class IsTelegramBot(BasePermission):
    """Allow only requests coming from a registered ``OrganizationBot``.

    Expected headers:
      * ``X-Telegram-Bot-Id`` — the bot's UUID.
      * ``X-Telegram-Internal-Secret`` — ``OrganizationBot.internal_secret``.

    Both must match a single active bot row. Missing, malformed, or
    mismatched values reject the request. The comparison uses
    ``hmac.compare_digest`` to avoid timing side channels.
    """

    def has_permission(self, request, view) -> bool:
        # Imported lazily so the auth layer doesn't pull the model graph
        # during module initialisation.
        from apps.notifications.models import OrganizationBot

        bot_id = request.headers.get("X-Telegram-Bot-Id", "")
        secret = request.headers.get("X-Telegram-Internal-Secret", "")
        if not (bot_id and secret):
            return False
        try:
            bot = OrganizationBot.objects.filter(
                id=bot_id, is_active=True,
            ).first()
        except (ValueError, TypeError):
            # Malformed UUID — refuse without leaking that detail.
            return False
        if bot is None:
            return False
        if not hmac.compare_digest(bot.internal_secret, secret):
            return False
        # Expose the resolved bot so the view/serializer can read
        # ``bot.organization`` without another round-trip.
        request.telegram_bot = bot
        return True
