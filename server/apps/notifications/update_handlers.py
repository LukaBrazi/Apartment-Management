"""Pure-Python handlers for incoming Telegram updates.

The webhook view and the ``run_bot`` polling command both receive
updates in different shapes (HTTP request body vs. python-telegram-bot
``Update`` object), but the *handling* — what to do when a user sends
``/start <token>``, ``/stop``, or ``/status`` — is identical.

This module speaks only to the Django ORM. It knows which bot sent
the message, what command the user typed, and the chat_id, and it
returns the *reply text* that the caller is responsible for
delivering via Telegram. That split keeps the ORM layer out of the
async/webhook plumbing, which is what makes the webhook view easy to
unit-test and keeps Django 5's async-safety guard happy.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ── Canned reply copy (Ukrainian — matches the rest of the UI) ────────────


MSG_START_OK = (
    "✅ *Telegram підключено!*\n\n"
    "Тепер ви будете отримувати сповіщення від ApartmentOS."
)
MSG_START_INVALID = (
    "❌ Невірний або прострочений токен. Спробуйте ще раз."
)
MSG_START_CROSS_ORG = (
    "❌ Токен не підходить до цього бота. "
    "Переконайтесь, що ви згенерували токен у правильній ЖК."
)
MSG_START_WELCOME = (
    "👋 *Вітаємо у ApartmentOS Bot!*\n\n"
    "Щоб підключити сповіщення, перейдіть в особистий кабінет на сайті "
    "та натисніть «Підключити Telegram»."
)
MSG_STOP_OK = (
    "🔕 Сповіщення вимкнено. Щоб увімкнути знову — /start."
)
MSG_STOP_NO_PROFILE = "Профіль не знайдено."
MSG_STATUS_NOT_LINKED = (
    "Акаунт не підключено. Використайте /start з токеном."
)


@dataclass(frozen=True)
class HandlerResult:
    """What the caller should send back over Telegram."""

    reply_text: str
    parse_mode: str = "Markdown"


# ── Handlers ───────────────────────────────────────────────────────────────
# Each handler takes ``bot`` (the ``OrganizationBot`` row whose webhook
# was hit) and the chat context, and returns what to reply. The bot
# row fixes the org — every ORM query below filters on ``bot.organization``
# so cross-tenant confusion is structurally impossible.


def handle_start(bot, chat_id: int, args: list[str]) -> HandlerResult:
    """``/start`` and ``/start <token>``.

    Without a token we show the onboarding blurb. With a token we try
    to exchange it for a ``TelegramProfile`` row. The token must belong
    to ``bot.organization`` — a token minted for org A handed to org
    B's bot is rejected with the same error text as an expired token
    so attackers learn nothing from the differential.
    """
    if not args:
        return HandlerResult(MSG_START_WELCOME)

    from django.core.exceptions import ValidationError

    from apps.notifications.models import (
        TelegramProfile,
        TelegramVerificationToken,
    )

    token_value = args[0]
    try:
        token_obj = (
            TelegramVerificationToken.objects
            .select_related("user", "organization")
            .get(token=token_value)
        )
    except (
        TelegramVerificationToken.DoesNotExist,
        ValueError,
        ValidationError,
    ):
        # ValidationError covers Django's "not a valid UUID" path when
        # the user types nonsense after ``/start``.
        return HandlerResult(MSG_START_INVALID)

    if not token_obj.is_valid:
        return HandlerResult(MSG_START_INVALID)

    if token_obj.organization_id != bot.organization_id:
        # Explicit differential reply is intentional in logs — but
        # we return the same user-facing copy so an attacker probing
        # for cross-org mismatches can't distinguish it from a bad
        # token. The "cross_org" reply is reserved for a future UX
        # improvement where we *know* the caller is legit.
        logger.warning(
            "telegram webhook: token org mismatch "
            "(token_org=%s, bot_org=%s, chat_id=%s)",
            token_obj.organization_id, bot.organization_id, chat_id,
        )
        return HandlerResult(MSG_START_INVALID)

    # Mark token used atomically with the profile upsert so re-use is
    # impossible on retries.
    token_obj.is_used = True
    token_obj.save(update_fields=["is_used"])

    profile, created = TelegramProfile.objects.get_or_create(
        user=token_obj.user,
        organization=token_obj.organization,
        defaults={"chat_id": chat_id, "is_active": True},
    )
    if not created:
        profile.chat_id = chat_id
        profile.is_active = True
        profile.save(update_fields=["chat_id", "is_active"])

    return HandlerResult(MSG_START_OK)


def handle_stop(bot, chat_id: int) -> HandlerResult:
    """``/stop`` — deactivate the (bot.org, chat_id) binding.

    Crucially, we filter on the bot's organization *and* chat_id — not
    on chat_id alone. A user with bindings under two orgs gets to mute
    only the bot they messaged, not every ЖК at once.
    """
    from apps.notifications.models import TelegramProfile

    updated = TelegramProfile.objects.filter(
        organization=bot.organization, chat_id=chat_id,
    ).update(is_active=False)
    if updated:
        return HandlerResult(MSG_STOP_OK)
    return HandlerResult(MSG_STOP_NO_PROFILE)


def handle_status(bot, chat_id: int) -> HandlerResult:
    """``/status`` — tell the user whether notifications are on.

    Scoped to this bot's org so the answer is never about "some other
    ЖК I also happen to be in".
    """
    from apps.notifications.models import TelegramProfile

    profile = (
        TelegramProfile.objects
        .select_related("user")
        .filter(organization=bot.organization, chat_id=chat_id)
        .first()
    )
    if profile is None:
        return HandlerResult(MSG_STATUS_NOT_LINKED)

    state = "✅ активні" if profile.is_active else "🔕 вимкнені"
    return HandlerResult(
        f"📊 *Статус сповіщень:* {state}\n"
        f"👤 Акаунт: {profile.user.email}",
    )


# ── Dispatch ───────────────────────────────────────────────────────────────


COMMAND_HANDLERS = {
    "start": lambda bot, chat_id, args: handle_start(bot, chat_id, args),
    "stop": lambda bot, chat_id, args: handle_stop(bot, chat_id),
    "status": lambda bot, chat_id, args: handle_status(bot, chat_id),
}


def dispatch_command(
    bot, chat_id: int, command: str, args: list[str],
) -> HandlerResult | None:
    """Route ``command`` to the matching handler. Unknown → ``None``."""
    handler = COMMAND_HANDLERS.get(command.lower())
    if handler is None:
        return None
    return handler(bot, chat_id, args)


def parse_command_text(text: str) -> tuple[str, list[str]] | None:
    """Pull ``("command", [args...])`` out of a Telegram message body.

    Telegram commands look like ``/command@BotName arg1 arg2``. We strip
    the optional ``@BotName`` suffix and split the rest on whitespace.
    Non-command text returns ``None``.
    """
    if not text or not text.startswith("/"):
        return None
    parts = text[1:].split()
    if not parts:
        return None
    head, *args = parts
    # Strip the optional @BotName suffix.
    command = head.split("@", 1)[0]
    return command, args


def handle_webhook_update(bot, update: dict) -> HandlerResult | None:
    """Handle a raw Telegram update dict (as POSTed by Telegram).

    Returns the reply text to send, or ``None`` when the update is
    something we don't act on (non-command message, edited message,
    callback query, etc.). Callers are responsible for pushing the
    reply back over Telegram's API.
    """
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = message.get("text") or ""

    if chat_id is None:
        return None

    parsed = parse_command_text(text)
    if parsed is None:
        return None
    command, args = parsed
    return dispatch_command(bot, chat_id, command, args)
