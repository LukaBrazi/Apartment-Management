"""Lock-down regex tests for the billing seed fixture (PR-13a).

These read ``billing_initial.json`` as plain text and verify the
canonical prices match the ApartmentOS price list. Anything that
diverges (stray edit during a rebase, accidental cents shift) makes
the test red.

Why text-level: a runtime fixture-load + DB query would be enough,
but it can be silenced by an unrelated regression. The text check is
deliberately blunt — every price gets its own assertion.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


SEED_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "billing_initial.json"
)


def _seed_text() -> str:
    return SEED_PATH.read_text(encoding="utf-8")


def _seed_json() -> list[dict]:
    return json.loads(_seed_text())


# ── SubscriptionPlan price lock-downs ────────────────────────────────────────


def test_seed_file_exists():
    assert SEED_PATH.exists(), f"Missing seed: {SEED_PATH}"


def test_starter_plan_price_5900():
    rows = _seed_json()
    starter = next(
        (r for r in rows if r["model"] == "billing.subscriptionplan"
         and r["fields"]["code"] == "starter"),
        None,
    )
    assert starter is not None, "Starter plan missing from seed"
    assert starter["fields"]["monthly_price_uah"] == "5900.00"
    assert starter["fields"]["max_apartments"] == 150
    assert starter["fields"]["max_users"] == 300


def test_business_plan_price_14900():
    rows = _seed_json()
    business = next(
        (r for r in rows if r["model"] == "billing.subscriptionplan"
         and r["fields"]["code"] == "business"),
        None,
    )
    assert business is not None
    assert business["fields"]["monthly_price_uah"] == "14900.00"


def test_professional_plan_price_29900():
    rows = _seed_json()
    pro = next(
        (r for r in rows if r["model"] == "billing.subscriptionplan"
         and r["fields"]["code"] == "professional"),
        None,
    )
    assert pro is not None
    assert pro["fields"]["monthly_price_uah"] == "29900.00"


def test_enterprise_plan_price_59900_unlimited():
    rows = _seed_json()
    ent = next(
        (r for r in rows if r["model"] == "billing.subscriptionplan"
         and r["fields"]["code"] == "enterprise"),
        None,
    )
    assert ent is not None
    assert ent["fields"]["monthly_price_uah"] == "59900.00"
    assert ent["fields"]["max_apartments"] is None
    assert ent["fields"]["max_users"] is None


# ── AddOn price lock-downs ───────────────────────────────────────────────────


@pytest.mark.parametrize("code,expected_price,expected_billing_type", [
    ("custom_domain", "2500.00", "one_time"),
    ("extended_branding", "8500.00", "one_time"),
    ("sms_setup", "4500.00", "one_time"),
    ("residents_import", "4500.00", "one_time"),
    ("payment_integration", "35000.00", "one_time"),
    ("admin_training", "2200.00", "one_time"),
    ("sms_subscription", "1200.00", "recurring_monthly"),
    ("priority_support_24_7", "4900.00", "recurring_monthly"),
])
def test_addon_price(code, expected_price, expected_billing_type):
    rows = _seed_json()
    addon = next(
        (r for r in rows if r["model"] == "billing.addon"
         and r["fields"]["code"] == code),
        None,
    )
    assert addon is not None, f"AddOn {code} missing from seed"
    assert addon["fields"]["price_uah"] == expected_price
    assert addon["fields"]["billing_type"] == expected_billing_type


def test_seed_has_4_plans():
    rows = _seed_json()
    plans = [r for r in rows if r["model"] == "billing.subscriptionplan"]
    assert len(plans) == 4


def test_seed_has_8_addons():
    rows = _seed_json()
    addons = [r for r in rows if r["model"] == "billing.addon"]
    assert len(addons) == 8


# ── Settings lock-down ───────────────────────────────────────────────────────


def test_base_settings_define_invoice_payer_envs():
    """Every INVOICE_PAYER_* env var lives in base.py with a default."""
    base_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "config" / "settings" / "base.py"
    )
    text = base_path.read_text(encoding="utf-8")
    # Each name read via env.str(...) (or env.int for INVOICE_DUE_DAYS).
    expected = [
        r"INVOICE_PAYER_LEGAL_NAME\s*=\s*env\.str",
        r"INVOICE_PAYER_TAX_ID\s*=\s*env\.str",
        r"INVOICE_PAYER_IBAN\s*=\s*env\.str",
        r"INVOICE_PAYER_BANK_NAME\s*=\s*env\.str",
        r"INVOICE_PAYER_TAX_NOTE\s*=\s*env\.str",
        r"INVOICE_DUE_DAYS\s*=\s*env\.int",
    ]
    for pattern in expected:
        assert re.search(pattern, text), (
            f"base.py missing INVOICE_PAYER lock-down setting: {pattern}"
        )


def test_billing_app_in_installed_apps():
    """``apps.billing`` must be in LOCAL_APPS in base.py."""
    base_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "config" / "settings" / "base.py"
    )
    text = base_path.read_text(encoding="utf-8")
    assert '"apps.billing"' in text, "apps.billing missing from LOCAL_APPS"
