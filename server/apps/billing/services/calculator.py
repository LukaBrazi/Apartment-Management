"""Pure-ish calculator service for invoice arithmetic (PR-13a).

Three entry points:

* :func:`calculate_recurring_invoice` — the monthly / annual subscription
  invoice (plan + active recurring add-ons − annual discount).
* :func:`calculate_onboarding_invoice` — sum of selected one-time add-ons
  by catalog code (e.g. setup fees on a fresh signup).
* :func:`calculate_proration_on_plan_change` — refund of unused old plan
  and charge for the new plan from change_date through next_billing_at.

Each function returns a dict shaped like
``{"line_items": [...], "subtotal": Decimal, "discount": Decimal, "total": Decimal}``
(proration returns its own three-key dict — see its docstring).

Money math goes through ``Decimal`` end-to-end, with explicit
``quantize(Decimal("0.01"))`` rounding at the boundary. This keeps the
results identical between Python's debug mode and prod.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from apps.billing.models import SubscriptionPlan
    from apps.organizations.models import Organization


CENTS = Decimal("0.01")
ANNUAL_DISCOUNT_RATE = Decimal("0.15")  # 15% off when paying annually


def _q(value: Decimal) -> Decimal:
    """Round a Decimal to two places (UAH cents)."""
    return value.quantize(CENTS)


# ── calculate_recurring_invoice ──────────────────────────────────────────────


def calculate_recurring_invoice(
    org: "Organization",
    period_start: date,
    period_end: date,
) -> dict:
    """Build the recurring (monthly / annual) invoice payload for ``org``.

    Returns a dict with:
        * ``line_items``: list of dicts (line_type, description, quantity,
          unit_price, total)
        * ``subtotal``: Decimal — sum of positive line totals (BEFORE
          discount).  The annual discount line, when present, is *also*
          appended to ``line_items`` with a negative ``total``, but the
          ``subtotal`` value itself is the pre-discount figure.
        * ``discount``: Decimal — the annual discount as a positive value
          (or ``0.00``).
        * ``total``: Decimal — subtotal − discount.

    During trial: every monetary value is zero and a single
    ``trial_credit`` line is emitted with the trial end date so the
    recipient sees what's going on.
    """
    sub = org.subscription
    line_items: list[dict] = []

    # Trial fast-path — return early with the single explanatory line.
    if sub.is_in_trial:
        line_items.append({
            "line_type": "trial_credit",
            "description": (
                f"Trial period (закінчується {sub.trial_ends_at:%Y-%m-%d})"
            ),
            "quantity": 1,
            "unit_price": Decimal("0.00"),
            "total": Decimal("0.00"),
        })
        return {
            "line_items": line_items,
            "subtotal": Decimal("0.00"),
            "discount": Decimal("0.00"),
            "total": Decimal("0.00"),
        }

    # Base subscription line.
    base_price = _q(sub.plan.monthly_price_uah)
    line_items.append({
        "line_type": "base_subscription",
        "description": f"Підписка {sub.plan.name}",
        "quantity": 1,
        "unit_price": base_price,
        "total": base_price,
    })

    # Recurring add-ons (only ``is_active=True`` and recurring billing).
    addon_qs = (
        org.addons
        .filter(is_active=True)
        .select_related("addon")
    )
    for org_addon in addon_qs:
        if not org_addon.is_recurring:
            continue
        if org_addon.is_custom_module:
            line_type = "custom_module"
        else:
            line_type = "addon_recurring"
        price = _q(org_addon.effective_price)
        line_items.append({
            "line_type": line_type,
            "description": org_addon.effective_name,
            "quantity": 1,
            "unit_price": price,
            "total": price,
        })

    # Subtotal = sum of positive line totals so far.
    subtotal = sum((Decimal(li["total"]) for li in line_items), Decimal("0.00"))
    subtotal = _q(subtotal)

    # Annual discount is applied AFTER all add-ons are summed.
    discount = Decimal("0.00")
    if sub.billing_period == "annual":
        discount = _q(subtotal * ANNUAL_DISCOUNT_RATE)
        line_items.append({
            "line_type": "annual_discount",
            "description": "Знижка за річну оплату (15%)",
            "quantity": 1,
            "unit_price": -discount,
            "total": -discount,
        })

    total = _q(subtotal - discount)
    return {
        "line_items": line_items,
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
    }


# ── calculate_onboarding_invoice ─────────────────────────────────────────────


def calculate_onboarding_invoice(
    org: "Organization",
    addon_codes: list[str] | tuple[str, ...],
) -> dict:
    """Build the onboarding (one-time add-ons) invoice payload.

    Looks up each code in the catalog. Recurring or unknown codes are
    silently skipped — the admin form only renders one-time options
    so an unknown code is a server-side bug or a stale form, both
    fail-closed.
    """
    from apps.billing.models import AddOn

    line_items: list[dict] = []
    if not addon_codes:
        return {
            "line_items": line_items,
            "subtotal": Decimal("0.00"),
            "discount": Decimal("0.00"),
            "total": Decimal("0.00"),
        }

    addons = AddOn.objects.filter(
        code__in=list(addon_codes),
        billing_type=AddOn.BILLING_ONE_TIME,
        is_active=True,
    )
    for addon in addons:
        price = _q(addon.price_uah)
        line_items.append({
            "line_type": "addon_one_time",
            "description": addon.name_uk,
            "quantity": 1,
            "unit_price": price,
            "total": price,
        })

    subtotal = sum((Decimal(li["total"]) for li in line_items), Decimal("0.00"))
    subtotal = _q(subtotal)
    return {
        "line_items": line_items,
        "subtotal": subtotal,
        "discount": Decimal("0.00"),
        "total": subtotal,
    }


# ── calculate_proration_on_plan_change ───────────────────────────────────────


def calculate_proration_on_plan_change(
    org: "Organization",
    new_plan: "SubscriptionPlan",
    change_date: date,
) -> dict:
    """Compute proration when the org swaps to ``new_plan`` mid-cycle.

    Algorithm:
        period_days = 30 if monthly else 365 (annual)
        days_remaining = (next_billing_at − change_date).days
        old_period_price = old.monthly_price * (period_days / 30)
        new_period_price = new.monthly_price * (period_days / 30)
        if annual: apply 15% discount to BOTH (already-paid old, new charge)
        refund_old = old_period_price * days_remaining / period_days
        charge_new = new_period_price * days_remaining / period_days
        net = refund_old − charge_new
            (positive = org is owed credit; negative = org owes us)

    Returns ``{"refund_old": Decimal, "charge_new": Decimal, "net": Decimal}``.
    """
    sub = org.subscription
    period_days = 365 if sub.billing_period == "annual" else 30
    days_remaining = (sub.next_billing_at - change_date).days

    if days_remaining <= 0:
        return {
            "refund_old": Decimal("0.00"),
            "charge_new": Decimal("0.00"),
            "net": Decimal("0.00"),
        }

    # Convert monthly price to period price (annual = monthly * 12).
    months_per_period = Decimal(period_days) / Decimal(30)
    old_period_price = sub.plan.monthly_price_uah * months_per_period
    new_period_price = new_plan.monthly_price_uah * months_per_period

    if sub.billing_period == "annual":
        # Annual is already discounted 15%, both directions.
        old_period_price = old_period_price * (Decimal("1") - ANNUAL_DISCOUNT_RATE)
        new_period_price = new_period_price * (Decimal("1") - ANNUAL_DISCOUNT_RATE)

    fraction = Decimal(days_remaining) / Decimal(period_days)
    refund_old = _q(old_period_price * fraction)
    charge_new = _q(new_period_price * fraction)
    net = _q(refund_old - charge_new)

    return {
        "refund_old": refund_old,
        "charge_new": charge_new,
        "net": net,
    }
