"""Celery tasks that deliver Telegram notifications.

PR-14 phase 3 rewire: each task now picks the right
``OrganizationBot`` for the notification's org via
``bot_resolver.get_bot_for_org`` and drops the message if the bot is
missing or the org has the feature flag off. Cross-tenant leaks that
existed in the pre-rewrite code (``notify_building_tenants_announcement``
sending to EVERY tenant on the platform) are gone — every query now
filters profiles by ``organization`` as well.

The queue payload no longer carries a bot token. Tasks receive the
``bot_id`` (UUID) and dereference it on the worker so the encrypted
token never sits in the Redis queue.
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

# Number of chat_ids per Redis task when broadcasting to many tenants.
# Keeps queue spikes manageable for large buildings (500+ tenants).
BROADCAST_CHUNK_SIZE = 25


# ── Helpers ────────────────────────────────────────────────────────────────


def _site_name() -> str:
    """Platform name for footers — falls back to 'ApartmentOS' if SITE_NAME is unset."""
    return getattr(settings, "SITE_NAME", "ApartmentOS")


def _org_of_issue(issue):
    """Best-effort ``Organization`` lookup for an Issue.

    Priority:
      1. ``issue.organization`` — post-PR-9 direct FK, always preferred.
      2. ``issue.unit.organization`` — older rows where the Issue's FK
         is NULL but the unit carries one.

    Returns ``None`` if neither is set; callers treat that as "skip".
    """
    if getattr(issue, "organization_id", None):
        return issue.organization
    unit = getattr(issue, "unit", None)
    return getattr(unit, "organization", None) if unit else None


# ── Tasks ──────────────────────────────────────────────────────────────────


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_telegram_message(self, bot_id: str, chat_id: int, text: str) -> None:
    """Send a single Telegram message through the specified bot.

    ``bot_id`` is the ``OrganizationBot.id`` UUID. The task fetches the
    row, pulls the decrypted token, and sends. Keeping the token off
    the queue reduces its at-rest exposure (Redis persists payloads).

    If the bot has gone missing or inactive since the caller scheduled
    the task (rare but possible in a rolling disable), we drop the
    message silently — the customer's intent was "pause notifications",
    not "error loudly".
    """
    from apps.notifications.models import OrganizationBot
    from apps.notifications.utils import send_message_sync

    try:
        bot = OrganizationBot.objects.filter(id=bot_id, is_active=True).first()
        if bot is None or not bot.is_configured:
            logger.info(
                "send_telegram_message: bot %s not configured, dropping", bot_id,
            )
            return
        token = bot.bot_token
        success = send_message_sync(chat_id, text, token)
        if not success:
            logger.warning(
                "telegram message not delivered: bot=%s chat_id=%s",
                bot_id,
                chat_id,
            )
    except Exception as exc:  # noqa: BLE001
        # Retry the *task*, not the individual send — send_message_sync
        # already swallows per-message errors.
        if self.request.retries >= self.max_retries:
            logger.error(
                "send_telegram_message exhausted retries bot=%s chat_id=%s: %s",
                bot_id,
                chat_id,
                exc,
            )
            return
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_telegram_broadcast(self, bot_id: str, chat_ids: list[int], text: str) -> None:
    """Fan-out a message to multiple chat_ids through one bot.

    Chunks into groups of BROADCAST_CHUNK_SIZE to avoid Redis queue spikes.
    Each chunk is dispatched as individual ``send_telegram_message`` tasks,
    so per-recipient retry semantics are preserved.
    """
    try:
        for i in range(0, len(chat_ids), BROADCAST_CHUNK_SIZE):
            chunk = chat_ids[i : i + BROADCAST_CHUNK_SIZE]
            for chat_id in chunk:
                send_telegram_message.delay(bot_id, chat_id, text)
    except Exception as exc:  # noqa: BLE001
        if self.request.retries >= self.max_retries:
            logger.error(
                "send_telegram_broadcast exhausted retries bot=%s: %s",
                bot_id,
                exc,
            )
            return
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_tenant_issue_status_changed(
    self, issue_id: str, old_status: str, new_status: str,
) -> None:
    """Notify the reporter that their issue's status changed."""
    try:
        from apps.issues.models import Issue
        from apps.notifications.bot_resolver import get_bot_for_org
        from apps.notifications.models import TelegramProfile

        issue = Issue.objects.select_related("reported_by").get(pk=issue_id)
        org = _org_of_issue(issue)
        bot = get_bot_for_org(org)
        if bot is None:
            return

        profile = TelegramProfile.objects.filter(
            user=issue.reported_by,
            organization=org,
            is_active=True,
            notify_issues=True,
        ).first()
        if not profile:
            return

        status_labels = {
            "reported": "📋 Подано",
            "accepted": "✅ Прийнято",
            "in_progress": "🔧 В роботі",
            "done": "🎉 Виконано",
            "rejected": "❌ Відхилено",
        }
        old_label = status_labels.get(old_status, old_status)
        new_label = status_labels.get(new_status, new_status)

        text = (
            f"🔔 *Заявка оновлена*\n"
            f"*{issue.title}*\n"
            f"Статус: {old_label} → {new_label}\n\n"
            f"_{_site_name()}_"
        )
        send_telegram_message.delay(str(bot.id), profile.chat_id, text)
    except Exception as exc:  # noqa: BLE001
        if self.request.retries >= self.max_retries:
            logger.error(
                "notify_tenant_issue_status_changed exhausted retries "
                "issue_id=%s: %s",
                issue_id,
                exc,
            )
            return
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_dispatchers_new_issue(self, issue_id: str) -> None:
    """Notify this org's dispatchers (is_staff=True) about a new issue."""
    try:
        from apps.issues.models import Issue
        from apps.notifications.bot_resolver import get_bot_for_org
        from apps.notifications.utils import get_active_dispatcher_chat_ids

        issue = Issue.objects.select_related("reported_by__profile").get(
            pk=issue_id,
        )
        org = _org_of_issue(issue)
        bot = get_bot_for_org(org)
        if bot is None:
            return

        chat_ids = get_active_dispatcher_chat_ids(org)
        if not chat_ids:
            return

        text = (
            f"📨 *Нова заявка*\n"
            f"*{issue.title}*\n"
            f"Від: "
            f"{issue.reported_by.get_full_name() or issue.reported_by.email}\n"
            f"Пріоритет: {issue.priority}\n\n"
            f"_{_site_name()}_"
        )
        for chat_id in chat_ids:
            send_telegram_message.delay(str(bot.id), chat_id, text)
    except Exception as exc:  # noqa: BLE001
        if self.request.retries >= self.max_retries:
            logger.error(
                "notify_dispatchers_new_issue exhausted retries "
                "issue_id=%s: %s",
                issue_id,
                exc,
            )
            return
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_worker_assigned(self, issue_id: str) -> None:
    """Notify the worker assigned to an issue (under the issue's org's bot)."""
    try:
        from apps.issues.models import Issue
        from apps.notifications.bot_resolver import get_bot_for_org
        from apps.notifications.models import TelegramProfile

        issue = Issue.objects.select_related("assigned_to").get(pk=issue_id)
        if not issue.assigned_to:
            return

        org = _org_of_issue(issue)
        bot = get_bot_for_org(org)
        if bot is None:
            return

        profile = TelegramProfile.objects.filter(
            user=issue.assigned_to,
            organization=org,
            is_active=True,
            notify_issues=True,
        ).first()
        if not profile:
            return

        text = (
            f"👷 *Вам призначено заявку*\n"
            f"*{issue.title}*\n"
            f"Пріоритет: {issue.priority}\n\n"
            f"_{_site_name()}_"
        )
        send_telegram_message.delay(str(bot.id), profile.chat_id, text)
    except Exception as exc:  # noqa: BLE001
        if self.request.retries >= self.max_retries:
            logger.error(
                "notify_worker_assigned exhausted retries issue_id=%s: %s",
                issue_id,
                exc,
            )
            return
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_building_tenants_announcement(self, announcement_id: str) -> None:
    """Notify every tenant of the announcement's org about a new announcement.

    Cross-tenant fix: pre-PR-14 this sent to every tenant on the
    platform. Now we derive the org from ``announcement.building`` and
    filter profiles to that org only.

    Fan-out goes through ``send_telegram_broadcast`` instead of a
    per-recipient loop so the Redis queue is not flooded when a building
    has hundreds of tenants.
    """
    try:
        from apps.notifications.bot_resolver import get_bot_for_org
        from apps.notifications.models import TelegramProfile
        from apps.posts.models import Announcement

        announcement = Announcement.objects.select_related(
            "building__organization",
        ).get(pk=announcement_id)
        org = getattr(announcement.building, "organization", None)
        bot = get_bot_for_org(org)
        if bot is None:
            return

        chat_ids = list(
            TelegramProfile.objects.filter(
                organization=org,
                is_active=True,
                notify_announcements=True,
                user__profile__occupation="tenant",
            ).values_list("chat_id", flat=True)
        )
        if not chat_ids:
            return

        text = (
            f"📢 *Нове оголошення*\n"
            f"*{announcement.title}*\n\n"
            f"_{_site_name()}_"
        )
        send_telegram_broadcast.delay(str(bot.id), chat_ids, text)
    except Exception as exc:  # noqa: BLE001
        if self.request.retries >= self.max_retries:
            logger.error(
                "notify_building_tenants_announcement exhausted retries "
                "announcement_id=%s: %s",
                announcement_id,
                exc,
            )
            return
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_tenant_pass_status(self, pass_id: str, new_status: str) -> None:
    """Notify tenant when their vehicle pass status changes.

    VehiclePass has two statuses:
      - ``pending``  — pass submitted, awaiting guard review.
      - ``closed``   — guard confirmed the vehicle has passed through.
    """
    try:
        from apps.notifications.bot_resolver import get_bot_for_org
        from apps.notifications.models import TelegramProfile
        from apps.passes.models import VehiclePass

        vehicle_pass = VehiclePass.objects.select_related(
            "tenant", "organization",
        ).get(pk=pass_id)
        org = getattr(vehicle_pass, "organization", None)
        bot = get_bot_for_org(org)
        if bot is None:
            return

        profile = TelegramProfile.objects.filter(
            user=vehicle_pass.tenant,
            organization=org,
            is_active=True,
            notify_passes=True,
        ).first()
        if not profile:
            return

        pass_status_labels = {
            "pending": "⏳ очікує перевірки",
            "closed": "✅ авто зафіксовано охоронцем",
        }
        status_label = pass_status_labels.get(new_status, f"оновлена: {new_status}")
        text = (
            f"🚗 *Перепустка {status_label}*\n"
            f"Авто: `{vehicle_pass.car_number}`\n\n"
            f"_{_site_name()}_"
        )
        send_telegram_message.delay(str(bot.id), profile.chat_id, text)
    except Exception as exc:  # noqa: BLE001
        if self.request.retries >= self.max_retries:
            logger.error(
                "notify_tenant_pass_status exhausted retries pass_id=%s: %s",
                pass_id,
                exc,
            )
            return
        raise self.retry(exc=exc)
