import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def get_bot_token() -> str:
    return getattr(settings, "TELEGRAM_BOT_TOKEN", "")


async def send_message_async(chat_id: int, text: str) -> bool:
    """Send a Telegram message. Returns True on success, False on failure."""
    try:
        from telegram import Bot
        from telegram.error import Forbidden, ChatMigrated, BadRequest

        bot = Bot(token=get_bot_token())
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
        )
        return True
    except Exception as Forbidden:
        logger.warning(f"Telegram: user blocked bot (chat_id={chat_id})")
        _deactivate_profile(chat_id)
        return False
    except Exception as e:
        logger.error(f"Telegram send error chat_id={chat_id}: {e}")
        return False


def _deactivate_profile(chat_id: int):
    """Deactivate TelegramProfile when user blocks the bot."""
    try:
        from apps.notifications.models import TelegramProfile
        TelegramProfile.objects.filter(chat_id=chat_id).update(is_active=False)
    except Exception as e:
        logger.error(f"Failed to deactivate TelegramProfile chat_id={chat_id}: {e}")


def get_active_dispatcher_chat_ids():
    """Return chat_ids of all active dispatchers (is_staff=True)."""
    from apps.notifications.models import TelegramProfile
    return list(
        TelegramProfile.objects.filter(
            is_active=True,
            notify_issues=True,
            user__is_staff=True,
        ).values_list("chat_id", flat=True)
    )


def get_active_guard_chat_ids():
    """Return chat_ids of all active guards."""
    from apps.notifications.models import TelegramProfile
    return list(
        TelegramProfile.objects.filter(
            is_active=True,
            notify_passes=True,
            user__profile__occupation="guard",
        ).select_related("user__profile").values_list("chat_id", flat=True)
    )
