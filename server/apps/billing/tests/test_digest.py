"""TDD tests for the morning TG billing digest (PR-18, Phase 1).

Covered behaviour for ``apps.billing.digest.build_billing_digest``:

* ``trial_expiring`` lists orgs whose trial ends within the next 7 days
  (today inclusive), sorted by soonest-first; further-out trials are
  excluded.
* ``draft_old_count`` / ``draft_old_top`` reflect only invoices whose
  ``status == "draft"`` AND were issued more than 3 days ago.
* ``overdue_approved_count`` / ``overdue_approved_top`` count invoices
  in approved/overdue status whose ``due_at`` is more than 10 days in
  the past.
* ``mrr_uah`` sums ``plan.monthly_price_uah`` only over subscriptions
  that are active, NOT paused, AND past their trial window
  (or never had one).

The fixtures here intentionally DO NOT rely on the auto-trial signal,
because the signal pins ``trial_ends_at`` to ``today + 60d`` which would
make most "in trial" / "out of trial" assertions noisy. We mutate
``trial_ends_at`` explicitly per test.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest


pytestmark = pytest.mark.django_db


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_org(director, *, name: str):
    """Create a bare Organization without relying on plan fixtures."""
    from apps.organizations.models import Organization
    return Organization.objects.create(
        name=name,
        type="housing_complex",
        owner=director,
    )


def _set_trial(sub, *, ends_at):
    """Force a specific trial_ends_at (signal default is today+60d)."""
    sub.trial_ends_at = ends_at
    sub.save(update_fields=["trial_ends_at"])


def _make_invoice(org, *, status, issued_at, due_at, total=Decimal("100.00")):
    from apps.billing.models import Invoice
    inv = Invoice(
        organization=org,
        issued_at=issued_at,
        due_at=due_at,
        period_start=issued_at,
        period_end=issued_at,
        subtotal_uah=total,
        total_uah=total,
        status=status,
    )
    inv.save()
    return inv


# ── trial_expiring ──────────────────────────────────────────────────────────


class TestBillingDigestTrialExpiring:
    def test_lists_orgs_with_trial_ending_within_7_days(
        self, director, starter_plan,
    ):
        from apps.billing.digest import build_billing_digest

        today = date.today()

        # Trial ends tomorrow → included
        org1 = _make_org(director, name="Org tomorrow")
        _set_trial(org1.subscription, ends_at=today + timedelta(days=1))

        # Trial ends in 5 days → included
        org2 = _make_org(director, name="Org 5 days")
        _set_trial(org2.subscription, ends_at=today + timedelta(days=5))

        # Trial ends in 30 days → excluded
        org3 = _make_org(director, name="Org 30 days")
        _set_trial(org3.subscription, ends_at=today + timedelta(days=30))

        # Trial already over → excluded
        org4 = _make_org(director, name="Org expired")
        _set_trial(org4.subscription, ends_at=today - timedelta(days=2))

        digest = build_billing_digest()

        names = [item["name"] for item in digest["trial_expiring"]]
        assert "Org tomorrow" in names
        assert "Org 5 days" in names
        assert "Org 30 days" not in names
        assert "Org expired" not in names
        # Sorted by soonest first
        assert names.index("Org tomorrow") < names.index("Org 5 days")

        # Days_left value
        days_map = {item["name"]: item["days_left"] for item in digest["trial_expiring"]}
        assert days_map["Org tomorrow"] == 1
        assert days_map["Org 5 days"] == 5


# ── draft invoices > 3 days old ─────────────────────────────────────────────


class TestBillingDigestDraftInvoices:
    def test_counts_only_draft_invoices_older_than_three_days(
        self, director, starter_plan,
    ):
        from apps.billing.digest import build_billing_digest
        from apps.billing.models import Invoice

        org = _make_org(director, name="Inv test org")
        today = date.today()

        # Recent draft (1 day) — excluded
        _make_invoice(
            org,
            status=Invoice.STATUS_DRAFT,
            issued_at=today - timedelta(days=1),
            due_at=today + timedelta(days=14),
        )
        # Old draft (4 days) — included
        old_4d = _make_invoice(
            org,
            status=Invoice.STATUS_DRAFT,
            issued_at=today - timedelta(days=4),
            due_at=today + timedelta(days=10),
        )
        # Older draft (7 days) — included
        old_7d = _make_invoice(
            org,
            status=Invoice.STATUS_DRAFT,
            issued_at=today - timedelta(days=7),
            due_at=today + timedelta(days=7),
        )
        # Approved old — excluded (different status)
        _make_invoice(
            org,
            status=Invoice.STATUS_APPROVED,
            issued_at=today - timedelta(days=10),
            due_at=today + timedelta(days=20),
        )

        digest = build_billing_digest()
        assert digest["draft_old_count"] == 2
        # Top contains both invoice numbers
        for inv in (old_4d, old_7d):
            assert inv.invoice_number in digest["draft_old_top"]


# ── approved-not-paid > 10 days overdue ─────────────────────────────────────


class TestBillingDigestOverdueApproved:
    def test_counts_approved_or_overdue_with_due_at_in_past_more_than_10_days(
        self, director, starter_plan,
    ):
        from apps.billing.digest import build_billing_digest
        from apps.billing.models import Invoice

        org = _make_org(director, name="Overdue test org")
        today = date.today()

        # Approved, due 5 days ago — NOT yet >10d overdue
        _make_invoice(
            org,
            status=Invoice.STATUS_APPROVED,
            issued_at=today - timedelta(days=20),
            due_at=today - timedelta(days=5),
        )
        # Approved, due 15 days ago — >10d overdue ⇒ included
        bad_approved = _make_invoice(
            org,
            status=Invoice.STATUS_APPROVED,
            issued_at=today - timedelta(days=30),
            due_at=today - timedelta(days=15),
        )
        # Already labelled overdue, 20 days ago — included
        bad_overdue = _make_invoice(
            org,
            status=Invoice.STATUS_OVERDUE,
            issued_at=today - timedelta(days=40),
            due_at=today - timedelta(days=20),
        )
        # Paid, due 30 days ago — excluded (status filter)
        _make_invoice(
            org,
            status=Invoice.STATUS_PAID,
            issued_at=today - timedelta(days=45),
            due_at=today - timedelta(days=30),
        )

        digest = build_billing_digest()
        assert digest["overdue_approved_count"] == 2
        for inv in (bad_approved, bad_overdue):
            assert inv.invoice_number in digest["overdue_approved_top"]


# ── MRR snapshot ────────────────────────────────────────────────────────────


class TestBillingDigestMRR:
    def test_mrr_sums_active_non_paused_post_trial_subscriptions_only(
        self, director, starter_plan, business_plan,
    ):
        from apps.billing.digest import build_billing_digest

        today = date.today()

        # 1) Active, post-trial, monthly Starter — INCLUDED (5900)
        a = _make_org(director, name="A active starter")
        _set_trial(a.subscription, ends_at=today - timedelta(days=1))

        # 2) Active, post-trial, monthly Business — INCLUDED (14900)
        b = _make_org(director, name="B active biz")
        sub_b = b.subscription
        sub_b.plan = business_plan
        sub_b.trial_ends_at = today - timedelta(days=2)
        sub_b.save(update_fields=["plan", "trial_ends_at"])

        # 3) Active, IN trial — EXCLUDED
        c = _make_org(director, name="C trial")
        _set_trial(c.subscription, ends_at=today + timedelta(days=10))

        # 4) Paused — EXCLUDED
        d = _make_org(director, name="D paused")
        sub_d = d.subscription
        sub_d.trial_ends_at = today - timedelta(days=5)
        sub_d.is_paused = True
        sub_d.save(update_fields=["trial_ends_at", "is_paused"])

        # 5) Inactive — EXCLUDED
        e = _make_org(director, name="E inactive")
        sub_e = e.subscription
        sub_e.trial_ends_at = today - timedelta(days=5)
        sub_e.is_active = False
        sub_e.save(update_fields=["trial_ends_at", "is_active"])

        digest = build_billing_digest()
        # 5900 + 14900 = 20800
        assert digest["mrr_uah"] == Decimal("20800.00")

    def test_mrr_zero_when_no_active_paying_subscriptions(
        self, director, starter_plan,
    ):
        from apps.billing.digest import build_billing_digest

        today = date.today()
        # Only one org, currently in trial — MRR should be 0
        c = _make_org(director, name="C trial only")
        _set_trial(c.subscription, ends_at=today + timedelta(days=10))

        digest = build_billing_digest()
        assert digest["mrr_uah"] == Decimal("0")


# ── Schema sanity ──────────────────────────────────────────────────────────


class TestBillingDigestSchema:
    def test_returns_all_expected_keys_even_on_empty_db(self):
        from apps.billing.digest import build_billing_digest

        digest = build_billing_digest()
        assert set(digest.keys()) == {
            "trial_expiring",
            "draft_old_count",
            "draft_old_top",
            "overdue_approved_count",
            "overdue_approved_top",
            "mrr_uah",
        }
        assert digest["trial_expiring"] == []
        assert digest["draft_old_count"] == 0
        assert digest["draft_old_top"] == []
        assert digest["overdue_approved_count"] == 0
        assert digest["overdue_approved_top"] == []
