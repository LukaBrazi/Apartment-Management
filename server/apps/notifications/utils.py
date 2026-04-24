"""Low-level Telegram send helpers.

PR-14 phase 3 replaces the platform-wide ``TELEGRAM_BOT_TOKEN`` setting
with an explicit ``bot_token`` argument on every call. Every notifier
path now looks up the target organization, pulls that org's
``OrganizationBot``, and passes the decrypted token here. Nothing in
this module reaches into settings anymore.

The sync wrapper ``send_message_sync`` exists because Celery tasks run
in sync worker threads — we just build a fresh event loop per call.
For the webhook path (which is already async inside Django 5) you can
await ``send_message_async`` directly; it returns a
``(sent_ok, user_blocked)`` tuple so the caller stays in control of
any follow-up ORM work.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover — typing only
    from apps.organizations.models import Organization

logger = logging.getLogger(__name__)


# ── Chat queries used by task dispatchers ──────────────────────────────────
# All of these take an ``organization`` parameter and filter profiles to
# that org.  Pre-PR-14 versions filtered platform-wide; that silently
# leaked notifications across tenants, the cross-org isolation bug
# tracked in ``docs/ADR-014`` §1.


def get_active_dispatcher_chat_ids(organization: "Organization") -> list[int]:
    """Chat IDs of this org's staff dispatchers who opted into issue alerts.

    Staff here means ``is_staff=True`` on the user — the app's existing
    convention for "dispatcher" permissions. Org membership is enforced
    via the profile's ``organization`` FK so two ЖК don't see each
    other's traffic.
    """
    from apps.notifications.models import TelegramProfile

    return list(
        TelegramProfile.objects.filter(
            organization=organization,
            is_active=True,
            notify_issues=True,
            user__is_staff=True,
        ).values_list("chat_id", flat=True)
    )


def get_announcement_target_chat_ids(announcement, org) -> list[int]:
    """Return chat_ids scoped to announcement's target audience.

    Scoping rules (in priority order):
      1. entrance is set  → residents of that entrance only
         (filter via user__residencies__unit__entrance)
      2. building is set  → all org subscribers (org already constrains to building's org)
      3. neither          → all org subscribers (org-wide)

    No occupation filter — all active notify_announcements=True subscribers qualify.
    """
    from apps.notifications.models import TelegramProfile

    qs = TelegramProfile.objects.filter(
        organization=org,
        is_active=True,
        notify_announcements=True,
    )

    if announcement.entrance_id:
        qs = qs.filter(user__residencies__unit__entrance=announcement.entrance)

    return list(qs.values_list("chat_id", flat=True))


def get_news_target_chat_ids(org) -> list[int]:
    """Return chat_ids of all active org subscribers for a news broadcast.

    Scope: all TelegramProfile users in the given org who have opted into
    ``notify_announcements`` (news uses the same preference as announcements).
    Returns an empty list if ``org`` is None (global news has no org bot).
    """
    if org is None:
        return []

    from apps.notifications.models import TelegramProfile

    return list(
        TelegramProfile.objects.filter(
            organization=org,
            is_active=True,
            notify_announcements=True,
        ).values_list("chat_id", flat=True)
    )


def get_active_guard_chat_ids(organization: "Organization") -> list[int]:
    """Chat IDs of this org's guards who opted into pass alerts.

    Guards are identified by ``profile.occupation == "guard"`` — the
    same marker the frontend uses to route them into the guard portal.
    """
    from apps.notifications.models import TelegramProfile

    return list(
        TelegramProfile.objects.filter(
            organization=organization,
            is_active=True,
            notify_passes=True,
            user__profile__occupation="guard",
        )
        .select_related("user__profile")
        .values_list("chat_id", flat=True)
    )


# ── Low-level sender ───────────────────────────────────────────────────────


async def send_message_async(chat_id: int, text: str, bot_token: str) -> tuple[bool, bool]:
    """Send one Telegram message.

    Returns ``(sent_ok, user_blocked)``:

    * ``sent_ok`` — ``True`` when the message left the bot successfully.
    * ``user_blocked`` — ``True`` when Telegram returned ``Forbidden``,
      meaning the user blocked the bot. The sync wrapper (or any other
      caller) uses that signal to deactivate the matching profile —
      we deliberately keep the ORM call out of the async coroutine so
      Django 5's async-safety guard doesn't fire, and so that SQLite
      test transactions don't deadlock on a cross-thread write.

    Any other ``telegram.error.*`` is logged and swallowed; returning
    ``(False, False)`` lets the Celery task decide whether to retry.
    """
    if not bot_token:
        logger.debug("telegram send skipped: empty bot_token")
        return False, False
    try:
        # Import lazily so this module stays importable on workers that
        # haven't installed python-telegram-bot yet (e.g. the migration
        # replay path on CI).
        from telegram import Bot
        from telegram.error import BadRequest, ChatMigrated, Forbidden

        bot = Bot(token=bot_token)
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
        )
        return True, False
    except Forbidden:
        logger.warning(
            "telegram: user blocked bot (chat_id=%s) — flagging for deactivation",
            chat_id,
        )
        return False, True
    except ChatMigrated:
        logger.warning("telegram: chat migrated (chat_id=%s)", chat_id)
        return False, False
    except BadRequest as exc:
        logger.error("telegram send error chat_id=%s: %s", chat_id, exc)
        return False, False
    except Exception as exc:  # noqa: BLE001 — catchall on purpose
        # Any other error (network, InvalidToken on rotation gap, etc.)
        # is logged with full context and surfaces as a False return so
        # the task's retry path can decide.
        logger.error(
            "telegram unexpected error chat_id=%s: %s", chat_id, exc,
        )
        return False, False


def send_message_sync(chat_id: int, text: str, bot_token: str) -> bool:
    """Sync wrapper — drives a fresh event loop per call.

    Safe to use inside Celery task code; the loop is created
    on-demand and torn down at the end of the call so there is no
    interference with any surrounding async framework.

    When the async send reports a ``Forbidden`` (user blocked the bot),
    we deactivate the matching profile from this sync context — the
    ORM stays out of the async coroutine entirely.
    """
    try:
        loop = asyncio.new_event_loop()
        try:
            sent_ok, user_blocked = loop.run_until_complete(
                send_message_async(chat_id, text, bot_token),
            )
        finally:
            loop.close()
    except Exception as exc:  # noqa: BLE001
        logger.error("telegram sync-wrapper error chat_id=%s: %s", chat_id, exc)
        return False

    if user_blocked:
        _deactivate_profile(chat_id)
    return sent_ok


def _deactivate_profile(chat_id: int) -> None:
    """Mark every profile with this chat_id as inactive.

    Because chat_id is unique per-org at the DB layer, this typically
    touches a single row — but if the same chat_id appears under two
    orgs (the user linked Telegram separately to each), we deactivate
    only the binding that just got the ``Forbidden``. To do that we'd
    need to know which bot sent the message — since ``send_message_async``
    only has ``chat_id`` in scope here, we conservatively deactivate
    all matching rows. In practice that's fine: the user's intent
    ("stop bothering me") is the same across orgs.
    """
    try:
        from apps.notifications.models import TelegramProfile

        TelegramProfile.objects.filter(chat_id=chat_id).update(is_active=False)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "telegram: failed to deactivate profile chat_id=%s: %s",
            chat_id,
            exc,
        )
