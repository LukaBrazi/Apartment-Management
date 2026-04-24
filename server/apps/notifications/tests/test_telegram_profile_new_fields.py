"""TDD red-phase tests for new TelegramProfile fields.

These tests are intentionally written BEFORE the production code /
migration changes and are expected to FAIL until the following fields
exist on ``apps.notifications.models.TelegramProfile``:

* ``notify_emergency``   — BooleanField, default=True
* ``notify_visits``      — BooleanField, default=False
* ``telegram_username``  — CharField(max_length=64, blank=True, null=True)

And until ``TelegramSettingsSerializer`` (and therefore the
``PATCH /api/v1/notifications/telegram/settings/`` endpoint backed by
``TelegramSettingsView``) exposes all three new fields while still
ignoring unknown fields silently (security / ModelSerializer contract).

Run with:
    pytest server/apps/notifications/tests/test_telegram_profile_new_fields.py -v
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.notifications.models import TelegramProfile
from apps.notifications.serializers import (
    TelegramSettingsSerializer,
    TelegramStatusSerializer,
)
from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationType,
    OrgRole,
)

User = get_user_model()

SETTINGS_URL = reverse("notifications:settings")


# ── Fixtures ───────────────────────────────────────────────────────────────
# ASCII slugs on purpose — until python-slugify lands on this branch,
# Cyrillic slugify() returns empty and collides with the demo org created
# by migration 0004. Same convention as test_telegram_profile_rescope.py.


@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="ОСББ Сонячний",
        slug="osbb-soniachnyi-newfields",
        type=OrganizationType.HOUSING_COMPLEX,
    )


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="olenka_nf",
        email="resident_nf@demo.com",
        password="Demo1234!",
        first_name="Олена",
        last_name="Коваль",
    )


@pytest.fixture
def member(db, org):
    u = User.objects.create_user(
        username="member_nf",
        email="member_nf@demo.com",
        password="Demo1234!",
        first_name="Петро",
        last_name="Коваленко",
    )
    OrganizationMembership.objects.create(
        user=u, organization=org, role=OrgRole.RESIDENT, is_active=True,
    )
    return u


@pytest.fixture
def profile(db, member, org):
    return TelegramProfile.objects.create(
        user=member,
        organization=org,
        chat_id=555001,
        is_active=True,
    )


@pytest.fixture
def api_client():
    return APIClient()


# ── Model tests ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTelegramProfileNewFieldsModel:
    """New fields must exist on the model with the specified defaults /
    nullability. These locks the migration contract."""

    def test_telegram_profile_has_notify_emergency_default_true(self, user, org):
        """``notify_emergency`` must exist and default to True — emergency
        alerts are opt-out, not opt-in."""
        p = TelegramProfile.objects.create(user=user, organization=org, chat_id=1)
        p.refresh_from_db()
        assert hasattr(p, "notify_emergency"), (
            "TelegramProfile must expose a 'notify_emergency' attribute."
        )
        assert p.notify_emergency is True, (
            "notify_emergency must default to True (opt-out semantics)."
        )

    def test_telegram_profile_has_notify_visits_default_false(self, user, org):
        """``notify_visits`` must exist and default to False — visit pings
        are opt-in to keep noise low."""
        p = TelegramProfile.objects.create(user=user, organization=org, chat_id=2)
        p.refresh_from_db()
        assert hasattr(p, "notify_visits"), (
            "TelegramProfile must expose a 'notify_visits' attribute."
        )
        assert p.notify_visits is False, (
            "notify_visits must default to False (opt-in semantics)."
        )

    def test_telegram_profile_has_telegram_username_nullable(self, user, org):
        """``telegram_username`` must be blank-/null-able and <=64 chars.
        Default rows (no username provided) store NULL, not empty string
        spam, so we can distinguish "never synced" from "explicitly empty"."""
        p = TelegramProfile.objects.create(user=user, organization=org, chat_id=3)
        p.refresh_from_db()
        assert hasattr(p, "telegram_username"), (
            "TelegramProfile must expose a 'telegram_username' attribute."
        )
        assert p.telegram_username is None, (
            "telegram_username must default to NULL when not provided."
        )

        # Meta sanity — ensure it's the expected field shape.
        field = TelegramProfile._meta.get_field("telegram_username")
        assert field.null is True, "telegram_username must be null=True"
        assert field.blank is True, "telegram_username must be blank=True"
        assert field.max_length == 64, "telegram_username must have max_length=64"

        # And that we can actually store a value.
        p.telegram_username = "olenka_tg"
        p.save(update_fields=["telegram_username"])
        p.refresh_from_db()
        assert p.telegram_username == "olenka_tg"


# ── Serializer tests ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTelegramSettingsSerializerNewFields:
    """The PATCH serializer (``TelegramSettingsSerializer``) must expose
    the three new fields so the frontend can toggle them. We also sanity-
    check the read serializer (``TelegramStatusSerializer``) surfaces
    notify_emergency / notify_visits / telegram_username on GET /status/."""

    def test_serializer_includes_notify_emergency(self, profile):
        assert "notify_emergency" in TelegramSettingsSerializer.Meta.fields, (
            "TelegramSettingsSerializer must include 'notify_emergency' "
            "in Meta.fields."
        )
        data = TelegramSettingsSerializer(profile).data
        assert "notify_emergency" in data
        assert data["notify_emergency"] is True

    def test_serializer_includes_notify_visits(self, profile):
        assert "notify_visits" in TelegramSettingsSerializer.Meta.fields, (
            "TelegramSettingsSerializer must include 'notify_visits' "
            "in Meta.fields."
        )
        data = TelegramSettingsSerializer(profile).data
        assert "notify_visits" in data
        assert data["notify_visits"] is False

    def test_serializer_includes_telegram_username(self, profile):
        """``telegram_username`` is surfaced on the status payload so the
        UI can show "@olenka_tg linked" instead of a raw chat_id. Having
        it on the settings serializer is also fine — the Model layer
        guarantees it's nullable, so a PATCH with a blank string must
        round-trip cleanly."""
        # Prefer: on status serializer (read-side display).
        status_fields = TelegramStatusSerializer.Meta.fields
        assert "telegram_username" in status_fields, (
            "TelegramStatusSerializer must include 'telegram_username' so "
            "the frontend can show the @handle next to the chat_id."
        )
        profile.telegram_username = "olenka_tg"
        profile.save(update_fields=["telegram_username"])
        data = TelegramStatusSerializer(profile).data
        assert data["telegram_username"] == "olenka_tg"


# ── View (PATCH) tests ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTelegramSettingsViewNewFields:
    """PATCH /telegram/settings/ must accept the new fields and persist
    them onto the caller's (user, org) TelegramProfile. Unknown fields
    must be silently ignored — ModelSerializer enforces this for free
    but we assert it explicitly to prevent accidental over-sharing
    if someone ever swaps in a plain ``serializers.Serializer``."""

    def test_patch_notify_emergency_updates_profile(
        self, api_client, member, org, profile,
    ):
        api_client.force_authenticate(member)
        resp = api_client.patch(
            SETTINGS_URL,
            {"notify_emergency": False},
            format="json",
            QUERY_STRING=f"organization={org.slug}",
        )
        assert resp.status_code == 200, resp.content
        profile.refresh_from_db()
        assert profile.notify_emergency is False
        # Response must echo the updated value so the UI can re-render
        # without a second GET.
        assert resp.json().get("notify_emergency") is False

    def test_patch_notify_visits_updates_profile(
        self, api_client, member, org, profile,
    ):
        api_client.force_authenticate(member)
        resp = api_client.patch(
            SETTINGS_URL,
            {"notify_visits": True},
            format="json",
            QUERY_STRING=f"organization={org.slug}",
        )
        assert resp.status_code == 200, resp.content
        profile.refresh_from_db()
        assert profile.notify_visits is True
        assert resp.json().get("notify_visits") is True

    def test_patch_telegram_username_is_ignored_by_settings_endpoint(
        self, api_client, member, org, profile,
    ):
        """Security: ``telegram_username`` is a bot-derived field and must NOT
        be writable through the settings PATCH endpoint.  Sending it in the
        payload must result in HTTP 200, but the field must remain unchanged
        (ModelSerializer silently drops fields not in Meta.fields)."""
        # Start with a known value — as if the bot had written it previously.
        profile.telegram_username = "original_handle"
        profile.save(update_fields=["telegram_username"])

        api_client.force_authenticate(member)
        resp = api_client.patch(
            SETTINGS_URL,
            {"telegram_username": "attacker_spoofed_handle", "notify_emergency": False},
            format="json",
            QUERY_STRING=f"organization={org.slug}",
        )
        assert resp.status_code == 200, resp.content

        profile.refresh_from_db()
        # The spoofed username must NOT have been written.
        assert profile.telegram_username == "original_handle", (
            "PATCH /settings/ must not allow clients to overwrite telegram_username. "
            "This field is set exclusively by the bot's /start handler."
        )
        # The response must not leak telegram_username (it's not in settings fields).
        body = resp.json()
        assert "telegram_username" not in body, (
            "settings endpoint response must not expose telegram_username."
        )
        # But the legit change did land.
        assert profile.notify_emergency is False

    def test_patch_unknown_field_ignored(
        self, api_client, member, org, profile,
    ):
        """Security: a caller must not be able to bump arbitrary fields
        (e.g. flip ``is_active``, change ``chat_id``, or inject a brand-
        new attribute) via the settings PATCH. ModelSerializer ignores
        keys that aren't declared in ``Meta.fields`` — this locks that
        behaviour in so a future refactor can't regress it."""
        original_chat_id = profile.chat_id
        original_is_active = profile.is_active

        api_client.force_authenticate(member)
        resp = api_client.patch(
            SETTINGS_URL,
            {
                # Not in Meta.fields — must be ignored.
                "chat_id": 999999999,
                "is_active": False,
                "user": 9999,
                "organization": 9999,
                "malicious_new_attr": "pwned",
                # Legit field so the request still "does something".
                "notify_emergency": False,
            },
            format="json",
            QUERY_STRING=f"organization={org.slug}",
        )

        assert resp.status_code == 200, resp.content

        profile.refresh_from_db()
        # Chat binding and activation must not be mutated by this endpoint.
        assert profile.chat_id == original_chat_id, (
            "PATCH /settings/ must not let callers overwrite chat_id."
        )
        assert profile.is_active == original_is_active, (
            "PATCH /settings/ must not let callers flip is_active."
        )
        # Ghost attribute must not materialise on the row.
        assert not hasattr(profile, "malicious_new_attr")
        # The legit change did land.
        assert profile.notify_emergency is False
        # And the response shape must not leak the ignored fields back.
        body = resp.json()
        assert "chat_id" not in body
        assert "is_active" not in body
        assert "malicious_new_attr" not in body
