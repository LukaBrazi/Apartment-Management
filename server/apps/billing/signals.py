"""Billing signals (PR-13a).

Three concerns:

1. **Trial auto-create** — every new Organization gets a 60-day Starter
   trial subscription on ``post_save`` (idempotent: ``get_or_create``).
2. **Apartment limit warn** — when a Unit is created and the org's plan
   says ``max_apartments=N`` is now exceeded, ping Telegram via
   ``send_telegram_message_task``. Soft-warn, no hard block.
3. **User limit warn** — same idea for ``max_users``, fired when an
   active OrganizationMembership is created.

The TG send is wrapped in ``try/except`` so signal failures never
break the underlying create/update — the warning is best-effort.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Trial auto-create ────────────────────────────────────────────────────────


@receiver(post_save, sender="organizations.Organization")
def create_default_subscription(sender, instance, created, **kwargs):
    """Auto-create a 60-day Starter trial when an Organization is created.

    If the Starter plan is missing (e.g. fresh DB before fixtures
    loaded, or a test that never seeded the plan), we exit silently —
    callers that need a subscription should explicitly seed the plan
    first. Idempotent via ``get_or_create``.
    """
    if not created:
        return

    from apps.billing.models import OrganizationSubscription, SubscriptionPlan

    starter = SubscriptionPlan.objects.filter(
        code="starter", is_active=True,
    ).first()
    if starter is None:
        return

    today = timezone.now().date()
    OrganizationSubscription.objects.get_or_create(
        organization=instance,
        defaults={
            "plan": starter,
            "billing_period": OrganizationSubscription.BILLING_MONTHLY,
            "started_at": today,
            "trial_ends_at": today + timedelta(days=60),
            "next_billing_at": today + timedelta(days=60),
        },
    )


# ── Soft-warn helpers ────────────────────────────────────────────────────────


def _send_limit_warning(text: str) -> None:
    """Best-effort Telegram warning. Never raises."""
    try:
        from apps.notifications.tasks import send_telegram_message_task
        send_telegram_message_task.delay(text)
    except Exception as exc:  # noqa: BLE001 — operational warn must never bubble
        logger.warning("Limit warning send failed: %s", exc)


def _format_warning(org_name: str, kind: str, plan_name: str, current: int, limit: int) -> str:
    return (
        f"⚠️ {org_name} перевищила ліміт {kind} тарифу {plan_name}: "
        f"{current}/{limit}"
    )


# ── Apartment limit ──────────────────────────────────────────────────────────


@receiver(post_save, sender="apartments.Unit")
def warn_on_apartment_limit_exceed(sender, instance, created, **kwargs):
    """Fire a TG warning when a Unit creation pushes the org over
    ``plan.max_apartments``.

    We only check on ``created=True`` — moves between entrances or
    edits don't change the org's count. ``max_apartments=None`` means
    "unlimited", which we silently skip.
    """
    if not created:
        return

    org = getattr(instance.entrance.building, "organization", None)
    if org is None:
        return

    sub = getattr(org, "subscription", None)
    if sub is None or sub.plan is None:
        return

    limit = sub.plan.max_apartments
    if limit is None:
        return

    from apps.apartments.models import Unit

    current = Unit.objects.filter(
        entrance__building__organization=org,
    ).count()
    if current > limit:
        _send_limit_warning(
            _format_warning(org.name, "квартир", sub.plan.name, current, limit)
        )


# ── User limit ───────────────────────────────────────────────────────────────


@receiver(post_save, sender="organizations.OrganizationMembership")
def warn_on_user_limit_exceed(sender, instance, created, **kwargs):
    """Same idea but for active organization memberships vs ``max_users``.

    We count distinct users with at least one active membership in the
    org, so a user with multiple memberships in different roles isn't
    double-counted.
    """
    if not created:
        return
    if not instance.is_active:
        return

    org = instance.organization
    sub = getattr(org, "subscription", None)
    if sub is None or sub.plan is None:
        return

    limit = sub.plan.max_users
    if limit is None:
        return

    from apps.organizations.models import OrganizationMembership

    current = (
        OrganizationMembership.objects
        .filter(organization=org, is_active=True)
        .values("user")
        .distinct()
        .count()
    )
    if current > limit:
        _send_limit_warning(
            _format_warning(org.name, "користувачів", sub.plan.name, current, limit)
        )
