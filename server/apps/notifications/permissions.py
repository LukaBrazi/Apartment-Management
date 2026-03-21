from django.conf import settings
from rest_framework.permissions import BasePermission


class IsTelegramBot(BasePermission):
    """
    Allows access only to requests with the correct Telegram internal secret header.
    Used to protect the /verify/ endpoint called by the bot.
    """
    def has_permission(self, request, view):
        secret = request.headers.get("X-Telegram-Internal-Secret", "")
        expected = getattr(settings, "TELEGRAM_INTERNAL_SECRET", "")
        return bool(expected and secret == expected)
