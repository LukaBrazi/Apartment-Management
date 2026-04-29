"""Organization-related Celery tasks (PR-11).

This module owns the asynchronous side of the **Organization Report
Email** feature: a Django Admin action lets a superuser select one or
more organizations and dispatch a per-org email containing an HTML
infographic report.  The actual rendering and sending happens here.

The report payload is intentionally lean — a single annotated query
fetches building / unit counts, a couple of follow-up aggregates fill
in resident and occupancy numbers, and the rest is template work.

The task is retried up to 3 times on transient SMTP / network errors;
permanent failures (missing org) log a warning and exit cleanly so the
Celery worker doesn't loop on a doomed job.
"""

from __future__ import annotations

import logging
from smtplib import SMTPException

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Count
from django.template.loader import render_to_string
from django.utils import timezone as dj_timezone
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


# Human-readable labels for the JSONField features on Organization.
# Order is intentional — keeps emails consistent across runs.
FEATURE_LABELS: list[tuple[str, str]] = [
    ("issues", "Заявки"),
    ("news", "Новини"),
    ("posts", "Пости"),
    ("announcements", "Оголошення"),
    ("passes", "Перепустки"),
    ("ratings", "Рейтинги"),
    ("payments", "Платежі"),
    ("reports", "Звіти"),
]


def _list_active_features(org) -> list[dict]:
    """Return a list of ``{name, label, active}`` dicts for the template.

    The Organization model stores feature flags in a JSONField (the
    ``_default_features`` factory in models.py seeds the canonical set).
    We walk the known FEATURE_LABELS list — anything in the JSON dict
    gets rendered with its proper label, and unknown keys are appended
    at the bottom so a future feature flag is at least visible without
    a code change here.

    Returns an empty list when the org has no features configured at
    all — the template treats that as "Лише базові функції" fallback.
    """
    features = getattr(org, "features", None) or {}
    if not features:
        return []

    seen: set[str] = set()
    out: list[dict] = []
    for key, label in FEATURE_LABELS:
        if key in features:
            out.append({
                "name": key,
                "label": label,
                "active": features.get(key) is True,
            })
            seen.add(key)

    # Surface unknown keys at the end (future-proof).
    for key, value in features.items():
        if key in seen:
            continue
        out.append({
            "name": key,
            "label": key.replace("_", " ").title(),
            "active": value is True,
        })

    return out


def _gather_org_report_data(org_id) -> dict:
    """Single-roundtrip aggregation for the org report payload.

    Pulls the Organization plus annotated counts of related buildings
    and units, then runs a couple of small follow-up queries for the
    resident and occupancy metrics.  Returns a context dict ready to
    be fed into the ``organizations/email/org_report.html`` template.

    Raises ``ValueError`` if the org doesn't exist — caller decides
    whether to log and skip or propagate.
    """
    from apps.apartments.models import Unit
    from apps.organizations.models import (
        Organization,
        OrganizationMembership,
        OrgRole,
    )

    org = (
        Organization.objects
        .filter(id=org_id)
        .annotate(
            n_buildings=Count("buildings", distinct=True),
            n_units=Count("buildings__entrances__units", distinct=True),
        )
        .first()
    )

    if org is None:
        raise ValueError(f"Organization {org_id} not found")

    # Active resident memberships — count distinct users so a user with
    # several memberships in the same org isn't double-counted.
    n_residents = (
        OrganizationMembership.objects
        .filter(
            organization=org,
            role=OrgRole.RESIDENT,
            is_active=True,
        )
        .values("user")
        .distinct()
        .count()
    )

    # Occupied units — units in the org that have at least one Residency
    # row attached. Residency has no `is_active` field; the model uses
    # start_date / end_date instead, so "occupied" here means "any
    # historical or current residency exists." That matches the metric
    # we want for now (PR-11 reports current footprint, not historical
    # vacancy). If we want strict "active today" later, add a date
    # filter — but matching the simpler semantic keeps tests stable.
    n_occupied = (
        Unit.objects
        .filter(organization=org, residencies__isnull=False)
        .distinct()
        .count()
    )

    n_units = org.n_units or 0
    pct = round(n_occupied * 100 / n_units, 1) if n_units else 0.0

    # SVG bar is 500px wide → 5px per percent. Clamp defensively in case
    # n_occupied somehow exceeds n_units (shouldn't, but cheap insurance).
    pct_px = max(0, min(500, round(pct * 5)))

    # 20-char ASCII bar — block char + light shade. Survives every email
    # client on the planet, including text-only ones.
    bar_filled = max(0, min(20, int(pct // 5)))
    ascii_bar = ("█" * bar_filled) + ("░" * (20 - bar_filled))

    return {
        "org_name": org.name,
        "org_slug": org.slug,
        "org_is_active": bool(getattr(org, "is_active", True)),
        "n_buildings": org.n_buildings or 0,
        "n_units": n_units,
        "n_residents": n_residents,
        "n_occupied": n_occupied,
        "occupancy_pct": pct,
        "occupancy_pct_px": pct_px,
        "occupancy_ascii": ascii_bar,
        "active_features": _list_active_features(org),
        "subscription_plan_text": "Не реалізовано (TODO PR-12)",
        "trial_status_text": "Не реалізовано (TODO PR-13)",
        "generated_at": dj_timezone.localtime(),
    }


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(SMTPException, OSError),
)
def send_organization_report_task(
    self,
    org_id,
    recipient_email: str,
) -> None:
    """Generate an HTML report for one organization and email it.

    Args:
        org_id: PK or UUID of the Organization. Accepts either since the
            admin action passes ``org.id`` (UUID) but tests sometimes use
            integer pkid — the underlying ``filter(id=org_id)`` handles both.
        recipient_email: where to send the report (typically
            ``request.user.email`` of the superuser invoking the action).

    Behavior:
        * Missing org → logs a warning and returns cleanly (no retry).
        * SMTP / OS errors → autoretry up to 3 times with 30s backoff.
        * Successful send → INFO log line with org name, id, recipient.
    """
    try:
        context = _gather_org_report_data(org_id)
    except ValueError:
        logger.warning("Org %s missing — skipping report", org_id)
        return

    context["recipient_email"] = recipient_email

    html_body = render_to_string(
        "organizations/email/org_report.html",
        context,
    )

    subject = f"\U0001F4CA Звіт організації — {context['org_name']}"
    text_fallback = (
        "Ваш email-клієнт не підтримує HTML. "
        "Звіт організації доступний тільки у HTML версії."
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_fallback,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email],
    )
    email.attach_alternative(html_body, "text/html")
    email.send()

    logger.info(
        "Org report sent: org=%s (id=%s) → %s",
        context["org_name"],
        org_id,
        recipient_email,
    )
