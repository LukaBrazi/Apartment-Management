"""Tests for TelegramStatusView — feature_enabled + bot_configured fields.

Contracts:
* Both ``feature_enabled`` and ``bot_configured`` appear in every response,
  regardless of whether the caller has a TelegramProfile.
* ``connected`` reflects whether a profile exists.
* ``feature_enabled`` mirrors ``org.is_feature_enabled(TELEGRAM_FEATURE_FLAG)``.
* ``bot_configured`` is True only when ``get_bot_for_org`` returns a bot.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.notifications.bot_resolver import TELEGRAM_FEATURE_FLAG
from apps.notifications.models import OrganizationBot, TelegramProfile
from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationType,
    OrgRole,
)

User = get_user_model()

STATUS_URL = reverse("notifications:status")


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org_feature_off(db):
    """Org with telegram_notifications feature disabled."""
    return Organization.objects.create(
        name="ОСББ Off",
        slug="osbb-off",
        type=OrganizationType.HOUSING_COMPLEX,
        features={TELEGRAM_FEATURE_FLAG: False},
    )


@pytest.fixture
def org_feature_on(db):
    """Org with telegram_notifications feature enabled."""
    return Organization.objects.create(
        name="ОСББ On",
        slug="osbb-on",
        type=OrganizationType.HOUSING_COMPLEX,
        features={TELEGRAM_FEATURE_FLAG: True},
    )


def _make_member(org, username, email):
    """Create a user and an active membership in the given org."""
    user = User.objects.create_user(
        username=username,
        email=email,
        password="Demo1234!",
        first_name="T",
        last_name="U",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.RESIDENT, is_active=True,
    )
    return user


def _make_bot(org):
    """Create an active primary OrganizationBot for the org."""
    bot = OrganizationBot(
        organization=org,
        bot_username="TestStatusBot",
        is_active=True,
        is_primary=True,
    )
    bot.bot_token = "111111111:AAE-test-status-bot"
    bot.save()
    return bot


# ── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_status_feature_disabled(api_client, org_feature_off):
    """Org feature off → connected=False, feature_enabled=False, bot_configured=False."""
    user = _make_member(org_feature_off, "user_off", "off@demo.com")
    api_client.force_authenticate(user)

    resp = api_client.get(STATUS_URL, {"organization": org_feature_off.slug})

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["feature_enabled"] is False
    assert body["bot_configured"] is False


@pytest.mark.django_db
def test_status_feature_enabled_no_bot(api_client, org_feature_on):
    """Feature on but no bot configured → connected=False, feature_enabled=True, bot_configured=False."""
    user = _make_member(org_feature_on, "user_no_bot", "nobot@demo.com")
    api_client.force_authenticate(user)

    resp = api_client.get(STATUS_URL, {"organization": org_feature_on.slug})

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["feature_enabled"] is True
    assert body["bot_configured"] is False


@pytest.mark.django_db
def test_status_feature_enabled_bot_configured_not_connected(api_client, org_feature_on):
    """Feature on, bot configured, no profile → connected=False, feature_enabled=True, bot_configured=True."""
    user = _make_member(org_feature_on, "user_no_profile", "noprofile@demo.com")
    _make_bot(org_feature_on)
    api_client.force_authenticate(user)

    resp = api_client.get(STATUS_URL, {"organization": org_feature_on.slug})

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["feature_enabled"] is True
    assert body["bot_configured"] is True


@pytest.mark.django_db
def test_status_connected(api_client, org_feature_on):
    """Feature on, bot configured, profile exists → connected=True, feature_enabled=True, bot_configured=True."""
    user = _make_member(org_feature_on, "user_linked", "linked@demo.com")
    _make_bot(org_feature_on)
    TelegramProfile.objects.create(
        user=user,
        organization=org_feature_on,
        chat_id=999001,
        is_active=True,
    )
    api_client.force_authenticate(user)

    resp = api_client.get(STATUS_URL, {"organization": org_feature_on.slug})

    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["feature_enabled"] is True
    assert body["bot_configured"] is True
