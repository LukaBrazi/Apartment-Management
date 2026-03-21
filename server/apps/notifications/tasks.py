import asyncio
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_telegram_message(self, chat_id: int, text: str):
    """Base task: send a single Telegram message."""
    from apps.notifications.utils import send_message_async
    try:
        success = _run_async(send_message_async(chat_id, text))
        if not success:
            logger.warning(f"Message not delivered to chat_id={chat_id}")
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_tenant_issue_status_changed(self, issue_id: str, old_status: str, new_status: str):
    """Notify tenant when their issue status changes."""
    try:
        from apps.issues.models import Issue
        from apps.notifications.models import TelegramProfile

        issue = Issue.objects.select_related("reported_by").get(pk=issue_id)
        profile = TelegramProfile.objects.filter(
            user=issue.reported_by,
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
            f"_Skandi Apartments_"
        )
        send_telegram_message.delay(profile.chat_id, text)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_dispatchers_new_issue(self, issue_id: str):
    """Notify all dispatchers (is_staff=True) about a new issue."""
    try:
        from apps.issues.models import Issue
        from apps.notifications.utils import get_active_dispatcher_chat_ids

        issue = Issue.objects.select_related("reported_by__profile").get(pk=issue_id)
        chat_ids = get_active_dispatcher_chat_ids()

        if not chat_ids:
            return

        text = (
            f"📨 *Нова заявка*\n"
            f"*{issue.title}*\n"
            f"Від: {issue.reported_by.get_full_name() or issue.reported_by.email}\n"
            f"Пріоритет: {issue.priority}\n\n"
            f"_Skandi Apartments_"
        )
        for chat_id in chat_ids:
            send_telegram_message.delay(chat_id, text)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_worker_assigned(self, issue_id: str):
    """Notify the worker assigned to an issue."""
    try:
        from apps.issues.models import Issue
        from apps.notifications.models import TelegramProfile

        issue = Issue.objects.select_related("assigned_to").get(pk=issue_id)
        if not issue.assigned_to:
            return

        profile = TelegramProfile.objects.filter(
            user=issue.assigned_to,
            is_active=True,
            notify_issues=True,
        ).first()

        if not profile:
            return

        text = (
            f"👷 *Вам призначено заявку*\n"
            f"*{issue.title}*\n"
            f"Пріоритет: {issue.priority}\n\n"
            f"_Skandi Apartments_"
        )
        send_telegram_message.delay(profile.chat_id, text)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_building_tenants_announcement(self, announcement_id: str):
    """Notify all tenants with active Telegram about a new announcement."""
    try:
        from apps.posts.models import Announcement
        from apps.notifications.models import TelegramProfile

        announcement = Announcement.objects.get(pk=announcement_id)
        chat_ids = TelegramProfile.objects.filter(
            is_active=True,
            notify_announcements=True,
            user__profile__occupation="tenant",
        ).values_list("chat_id", flat=True)

        text = (
            f"📢 *Нове оголошення*\n"
            f"*{announcement.title}*\n\n"
            f"_Skandi Apartments_"
        )
        for chat_id in chat_ids:
            send_telegram_message.delay(chat_id, text)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_tenant_pass_status(self, pass_id: str, new_status: str):
    """Notify tenant when their vehicle pass is approved/closed."""
    try:
        from apps.passes.models import VehiclePass
        from apps.notifications.models import TelegramProfile

        vehicle_pass = VehiclePass.objects.select_related("tenant").get(pk=pass_id)
        profile = TelegramProfile.objects.filter(
            user=vehicle_pass.tenant,
            is_active=True,
            notify_passes=True,
        ).first()

        if not profile:
            return

        status_text = "✅ підтверджена" if new_status == "closed" else f"оновлена: {new_status}"
        text = (
            f"🚗 *Перепустка {status_text}*\n"
            f"Авто: `{vehicle_pass.car_number}`\n\n"
            f"_Skandi Apartments_"
        )
        send_telegram_message.delay(profile.chat_id, text)
    except Exception as exc:
        raise self.retry(exc=exc)
