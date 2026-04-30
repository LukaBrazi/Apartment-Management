"""Morning Telegram digest helpers — billing health for the CEO (PR-18).

The digest answers the questions the CEO actually asks at 09:00:

* **Trial expiring** — which orgs roll off their 60-day trial in the
  next 7 days? (head-up to either reach out or pre-bill.)
* **Stale drafts** — invoices left in ``draft`` for more than 3 days
  almost always mean somebody forgot to send them.
* **Overdue approved** — sent invoices that have been past their
  ``due_at`` for more than 10 days. The 10-day grace period maps to
  our standard "we send a reminder, then we follow up".
* **MRR snapshot** — total monthly recurring revenue assuming every
  active, non-paused, post-trial subscription paid the catalogue price
  for its plan. Add-ons are NOT counted yet (PR-18 keeps the surface
  small; recurring add-on MRR is a separate follow-up).

Only the **shape** of the returned dict is contractual — the renderer
in ``apps.common.tasks`` walks the keys and is the only consumer.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone


# How many trial-expiring orgs to include in the inline list. Anything
# beyond this stays as a count-only footer in the renderer.
TRIAL_LIST_LIMIT = 10
# How many invoice numbers to surface as "top X" hints.
INVOICE_TOP_LIMIT = 3
# Threshold above which a draft invoice is considered "stale".
DRAFT_STALE_DAYS = 3
# Threshold above which an approved/overdue invoice is "really overdue".
OVERDUE_DAYS = 10
# Trial-expiring lookahead window.
TRIAL_LOOKAHEAD_DAYS = 7


def build_billing_digest() -> dict:
    """Return today's billing snapshot for the morning TG digest.

    Returns
    -------
    dict
        Keys:
            * ``trial_expiring`` — list of ``{"name", "days_left"}``,
              soonest first, capped to TRIAL_LIST_LIMIT.
            * ``draft_old_count`` — number of stale draft invoices.
            * ``draft_old_top`` — invoice numbers (most recent first),
              capped to INVOICE_TOP_LIMIT.
            * ``overdue_approved_count`` — number of approved/overdue
              invoices past 10 days due.
            * ``overdue_approved_top`` — invoice numbers (most overdue
              first), capped to INVOICE_TOP_LIMIT.
            * ``mrr_uah`` — Decimal sum of monthly plan prices.
    """
    # Lazy imports keep this module import-time cheap and avoid app-loading
    # ordering issues when the CommonConfig.ready() chain runs.
    from apps.billing.models import Invoice, OrganizationSubscription

    today = timezone.localdate()

    # ── Trial expiring soon ────────────────────────────────────────────────
    trial_qs = (
        OrganizationSubscription.objects.filter(
            is_active=True,
            trial_ends_at__gte=today,
            trial_ends_at__lte=today + timedelta(days=TRIAL_LOOKAHEAD_DAYS),
        )
        .select_related("organization", "plan")
        .order_by("trial_ends_at")[:TRIAL_LIST_LIMIT]
    )
    trial_expiring = [
        {
            "name": sub.organization.name,
            "days_left": (sub.trial_ends_at - today).days,
        }
        for sub in trial_qs
    ]

    # ── Draft invoices > 3 days old ────────────────────────────────────────
    # Invoice has no auto_now_add ``created_at``; ``issued_at`` (DateField,
    # default=today) is the closest analogue and is what the admin/calculator
    # set when minting the row. "Older than 3 days" therefore means
    # ``issued_at < today - 3 days``.
    draft_old_qs = Invoice.objects.filter(
        status=Invoice.STATUS_DRAFT,
        issued_at__lt=today - timedelta(days=DRAFT_STALE_DAYS),
    )
    draft_old_count = draft_old_qs.count()
    draft_old_top = list(
        draft_old_qs.order_by("-issued_at", "-id").values_list(
            "invoice_number", flat=True,
        )[:INVOICE_TOP_LIMIT]
    )

    # ── Approved-or-overdue, ``due_at`` > 10 days in the past ──────────────
    overdue_qs = Invoice.objects.filter(
        status__in=[Invoice.STATUS_APPROVED, Invoice.STATUS_OVERDUE],
        due_at__lt=today - timedelta(days=OVERDUE_DAYS),
    )
    overdue_approved_count = overdue_qs.count()
    overdue_approved_top = list(
        overdue_qs.order_by("due_at", "id").values_list(
            "invoice_number", flat=True,
        )[:INVOICE_TOP_LIMIT]
    )

    # ── MRR snapshot ───────────────────────────────────────────────────────
    # Active, non-paused, NOT-currently-in-trial subs sum their plan price.
    # ``trial_ends_at < today`` covers the rolled-off trials.
    # ``trial_ends_at IS NULL`` covers the rare bypass / legacy rows.
    mrr_value = (
        OrganizationSubscription.objects.filter(
            is_active=True,
            is_paused=False,
        )
        .filter(Q(trial_ends_at__lt=today) | Q(trial_ends_at__isnull=True))
        .aggregate(total=Sum("plan__monthly_price_uah"))
        ["total"]
    )
    mrr_uah = mrr_value if mrr_value is not None else Decimal("0")

    return {
        "trial_expiring": trial_expiring,
        "draft_old_count": draft_old_count,
        "draft_old_top": draft_old_top,
        "overdue_approved_count": overdue_approved_count,
        "overdue_approved_top": overdue_approved_top,
        "mrr_uah": mrr_uah,
    }
