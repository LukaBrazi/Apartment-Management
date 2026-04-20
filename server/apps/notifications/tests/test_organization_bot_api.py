"""Tests for the super_admin OrganizationBot REST API (PR-14 phase 6).

Contract
--------
* Only ``is_superuser=True`` callers see or mutate these rows; every
  other role — director, admin, resident, anonymous — gets 403.
* ``bot_token`` is write-only.  List/retrieve responses must *not*
  include the raw token under any key, and the masked preview is what
  the UI renders.
* The ``test`` action updates ``last_test_ok`` / ``last_test_error``
  on the row and surfaces username-mismatch as a failure so the
  frontend stops showing misconfigured bots as healthy.
* ``set_webhook`` requires ``PLATFORM_PUBLIC_URL`` — otherwise we
  refuse to call Telegram with an empty URL.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.notifications.models import OrganizationBot
from apps.notifications.telegram_api import TelegramAPIResult
from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationType,
    OrgRole,
)

User = get_user_model()


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="ОСББ Test", slug="osbb-test",
        type=OrganizationType.HOUSING_COMPLEX,
    )


@pytest.fixture
def superuser(db):
    user = User.objects.create_user(
        username="super", email="super@demo.com", password="Demo1234!",
        is_staff=True, is_superuser=True,
        first_name="S", last_name="U",
    )
    return user


@pytest.fixture
def director(db, org):
    user = User.objects.create_user(
        username="director", email="director@demo.com", password="Demo1234!",
        is_staff=True, is_superuser=False,
        first_name="D", last_name="I",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.DIRECTOR, is_active=True,
    )
    return user


@pytest.fixture
def org_admin(db, org):
    user = User.objects.create_user(
        username="orgadmin", email="orgadmin@demo.com", password="Demo1234!",
        is_staff=True, is_superuser=False,
        first_name="A", last_name="D",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.ADMIN, is_active=True,
    )
    return user


@pytest.fixture
def resident(db, org):
    user = User.objects.create_user(
        username="res", email="res@demo.com", password="Demo1234!",
        is_staff=False, is_superuser=False,
        first_name="R", last_name="E",
    )
    OrganizationMembership.objects.create(
        user=user, organization=org, role=OrgRole.RESIDENT, is_active=True,
    )
    return user


@pytest.fixture
def bot(db, org):
    bot = OrganizationBot(
        organization=org,
        bot_username="AlphaBot",
        is_active=True,
        is_primary=True,
    )
    bot.bot_token = "123456789:AAE-alpha-secret"
    bot.save()
    return bot


def _list_url() -> str:
    return reverse("notifications:telegram-bots-list")


def _detail_url(bot) -> str:
    return reverse("notifications:telegram-bots-detail", kwargs={"id": bot.id})


def _action_url(bot, action: str) -> str:
    return reverse(
        f"notifications:telegram-bots-{action}", kwargs={"id": bot.id},
    )


# ── Permissions: super_admin only ─────────────────────────────────────────


@pytest.mark.django_db
class TestPermissions:
    def test_anonymous_gets_401(self, api_client, bot):
        resp = api_client.get(_list_url())
        assert resp.status_code in (401, 403)

    def test_resident_gets_403(self, api_client, resident, bot):
        api_client.force_authenticate(resident)
        resp = api_client.get(_list_url())
        assert resp.status_code == 403

    def test_director_gets_403(self, api_client, director, bot):
        """CEO directive — тілтки super_admin.  Director must NOT see bots."""
        api_client.force_authenticate(director)
        assert api_client.get(_list_url()).status_code == 403
        assert api_client.get(_detail_url(bot)).status_code == 403
        assert api_client.patch(
            _detail_url(bot),
            data={"is_active": False}, format="json",
        ).status_code == 403

    def test_admin_role_gets_403(self, api_client, org_admin, bot):
        api_client.force_authenticate(org_admin)
        assert api_client.get(_list_url()).status_code == 403

    def test_superuser_gets_200(self, api_client, superuser, bot):
        api_client.force_authenticate(superuser)
        resp = api_client.get(_list_url())
        assert resp.status_code == 200


# ── List / Retrieve: token never leaks ────────────────────────────────────


@pytest.mark.django_db
class TestReadEndpoints:
    def test_list_returns_masked_and_hides_raw_token(
        self, api_client, superuser, bot,
    ):
        api_client.force_authenticate(superuser)
        resp = api_client.get(_list_url())
        assert resp.status_code == 200
        # DRF default pagination might wrap in "results".
        body = resp.json()
        results = body["results"] if isinstance(body, dict) else body
        assert len(results) == 1
        item = results[0]
        assert item["bot_username"] == "AlphaBot"
        # Masked preview keeps the bot id (before ':'), hides the secret
        # body, and keeps the last 4 chars.
        assert item["bot_token_masked"].startswith("123456789:")
        assert "alpha-secret" not in str(item)
        # Raw token must not be present under any key.
        assert "bot_token" not in item or item.get("bot_token") in ("", None)

    def test_retrieve_shape(self, api_client, superuser, bot):
        api_client.force_authenticate(superuser)
        resp = api_client.get(_detail_url(bot))
        assert resp.status_code == 200
        body = resp.json()
        assert body["organization_slug"] == bot.organization.slug
        assert body["is_configured"] is True

    @override_settings(PLATFORM_PUBLIC_URL="https://apartmentos.org")
    def test_webhook_url_populated(self, api_client, superuser, bot):
        api_client.force_authenticate(superuser)
        body = api_client.get(_detail_url(bot)).json()
        assert body["webhook_url"].endswith(
            f"/webhook/{bot.organization.slug}/",
        )


# ── Create: token is encrypted, not round-tripped ─────────────────────────


@pytest.mark.django_db
class TestCreate:
    def test_create_encrypts_token_and_stamps_creator(
        self, api_client, superuser, org,
    ):
        api_client.force_authenticate(superuser)
        resp = api_client.post(
            _list_url(),
            data={
                "organization": org.pkid,
                "bot_username": "FreshBot",
                "bot_token": "42:AAE-fresh",
                "is_active": True,
                "is_primary": True,
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content
        bot = OrganizationBot.objects.get(bot_username="FreshBot")
        # The setter encrypts via Fernet, so the plaintext must not appear.
        assert "AAE-fresh" not in bot.encrypted_token
        assert bot.bot_token == "42:AAE-fresh"
        # Creator stamped.
        assert bot.created_by_id == superuser.pk


# ── Update: blank bot_token preserves existing token ──────────────────────


@pytest.mark.django_db
class TestUpdate:
    def test_patch_without_token_preserves_existing(
        self, api_client, superuser, bot,
    ):
        api_client.force_authenticate(superuser)
        original_ciphertext = bot.encrypted_token
        resp = api_client.patch(
            _detail_url(bot),
            data={"bot_username": "AlphaBotRenamed"},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        bot.refresh_from_db()
        assert bot.bot_username == "AlphaBotRenamed"
        # Token ciphertext untouched — original encrypted value is
        # preserved so a rename doesn't wipe credentials.
        assert bot.encrypted_token == original_ciphertext

    def test_patch_with_token_replaces(self, api_client, superuser, bot):
        api_client.force_authenticate(superuser)
        resp = api_client.patch(
            _detail_url(bot),
            data={"bot_token": "999:REPLACED"},
            format="json",
        )
        assert resp.status_code == 200
        bot.refresh_from_db()
        assert bot.bot_token == "999:REPLACED"


# ── Test action ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTestAction:
    def test_success_records_and_responds(
        self, api_client, superuser, bot,
    ):
        api_client.force_authenticate(superuser)
        with patch(
            "apps.notifications.views.tg_get_me",
            return_value=TelegramAPIResult(
                ok=True, data={"username": "AlphaBot"},
            ),
        ):
            resp = api_client.post(_action_url(bot, "test"))
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        bot.refresh_from_db()
        assert bot.last_test_ok is True
        assert bot.last_tested_at is not None

    def test_username_mismatch_is_failure(
        self, api_client, superuser, bot,
    ):
        api_client.force_authenticate(superuser)
        with patch(
            "apps.notifications.views.tg_get_me",
            return_value=TelegramAPIResult(
                ok=True, data={"username": "SomeoneElseBot"},
            ),
        ):
            resp = api_client.post(_action_url(bot, "test"))
        body = resp.json()
        assert body["ok"] is False
        assert "SomeoneElseBot" in body["error"]
        bot.refresh_from_db()
        assert bot.last_test_ok is False

    def test_unauthorized_token_records_error(
        self, api_client, superuser, bot,
    ):
        api_client.force_authenticate(superuser)
        with patch(
            "apps.notifications.views.tg_get_me",
            return_value=TelegramAPIResult(ok=False, error="Unauthorized"),
        ):
            resp = api_client.post(_action_url(bot, "test"))
        body = resp.json()
        assert body["ok"] is False
        assert body["error"] == "Unauthorized"
        bot.refresh_from_db()
        assert bot.last_test_error == "Unauthorized"


# ── set_webhook / delete_webhook ──────────────────────────────────────────


@pytest.mark.django_db
class TestSetWebhook:
    @override_settings(PLATFORM_PUBLIC_URL="https://apartmentos.org")
    def test_success_passes_url_and_secret(
        self, api_client, superuser, bot,
    ):
        api_client.force_authenticate(superuser)
        with patch(
            "apps.notifications.views.tg_set_webhook",
            return_value=TelegramAPIResult(ok=True),
        ) as mock:
            resp = api_client.post(_action_url(bot, "set-webhook"))
        assert resp.status_code == 200
        kwargs = mock.call_args.kwargs
        assert kwargs["url"].endswith(f"/webhook/{bot.organization.slug}/")
        assert kwargs["secret_token"] == bot.webhook_secret

    @override_settings(PLATFORM_PUBLIC_URL="")
    def test_refuses_without_platform_public_url(
        self, api_client, superuser, bot,
    ):
        api_client.force_authenticate(superuser)
        with patch("apps.notifications.views.tg_set_webhook") as mock:
            resp = api_client.post(_action_url(bot, "set-webhook"))
        assert resp.status_code == 400
        mock.assert_not_called()

    @override_settings(PLATFORM_PUBLIC_URL="https://apartmentos.org")
    def test_surfaces_telegram_error(self, api_client, superuser, bot):
        api_client.force_authenticate(superuser)
        with patch(
            "apps.notifications.views.tg_set_webhook",
            return_value=TelegramAPIResult(
                ok=False, error="Bad Request: bad webhook",
            ),
        ):
            resp = api_client.post(_action_url(bot, "set-webhook"))
        assert resp.status_code == 400
        assert "bad webhook" in str(resp.json()).lower()


@pytest.mark.django_db
class TestDeleteWebhook:
    def test_success(self, api_client, superuser, bot):
        api_client.force_authenticate(superuser)
        with patch(
            "apps.notifications.views.tg_delete_webhook",
            return_value=TelegramAPIResult(ok=True),
        ) as mock:
            resp = api_client.post(_action_url(bot, "delete-webhook"))
        assert resp.status_code == 200
        mock.assert_called_once_with(bot.bot_token)


# ── Organizations picker ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestOrganizationsAction:
    """The super_admin bot UI needs a flat org list for the create form.

    We ship it on the bot viewset (not the orgs viewset) so the
    frontend only needs one permission — IsSuperAdmin — rather than
    mixing bot permissions with the member-facing orgs API.
    """

    def test_superuser_sees_all_orgs(self, api_client, superuser, org):
        api_client.force_authenticate(superuser)
        # Second org to prove it's not a single-row fluke.
        Organization.objects.create(
            name="ОСББ Second", slug="osbb-second",
            type=OrganizationType.HOUSING_COMPLEX,
        )
        url = reverse("notifications:telegram-bots-organizations")
        resp = api_client.get(url)
        assert resp.status_code == 200
        body = resp.json()
        slugs = {row["slug"] for row in body}
        assert {"osbb-test", "osbb-second"} <= slugs
        # Each entry carries pkid (FK target) + slug + name for the UI.
        sample = body[0]
        assert {"pkid", "id", "name", "slug", "is_active"} <= set(sample)

    def test_director_forbidden(self, api_client, director):
        api_client.force_authenticate(director)
        url = reverse("notifications:telegram-bots-organizations")
        assert api_client.get(url).status_code == 403
