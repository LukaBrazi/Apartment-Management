"""Tests for ``TelegramWebhookView`` — PR-14 phase 5.

The webhook is the single highest-value endpoint in the Telegram
integration: it's the one Telegram talks to, it's on the public
internet, and a soft spot here would let anyone trigger our handlers
against any organisation. The tests below lock in the three things
that matter:

1. The secret check is strict — no secret, wrong secret, or a secret
   that belongs to another org must return 403.
2. A valid request dispatches to the shared ``handle_webhook_update``
   with the bot whose org matches the URL slug.
3. We always 200 on a successfully-authenticated request, even when
   the handler fails, so Telegram stops retrying.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.notifications.models import OrganizationBot
from apps.organizations.models import Organization, OrganizationType


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org_a(db):
    return Organization.objects.create(
        name="ОСББ A",
        slug="osbb-a",
        type=OrganizationType.HOUSING_COMPLEX,
    )


@pytest.fixture
def org_b(db):
    return Organization.objects.create(
        name="ОСББ B",
        slug="osbb-b",
        type=OrganizationType.HOUSING_COMPLEX,
    )


@pytest.fixture
def bot_a(db, org_a):
    bot = OrganizationBot(
        organization=org_a,
        bot_username="AlphaBot",
        is_active=True,
        is_primary=True,
    )
    bot.bot_token = "123:AAE-alpha"
    bot.save()
    return bot


@pytest.fixture
def bot_b(db, org_b):
    bot = OrganizationBot(
        organization=org_b,
        bot_username="BetaBot",
        is_active=True,
        is_primary=True,
    )
    bot.bot_token = "456:AAE-beta"
    bot.save()
    return bot


def _webhook_url(slug: str) -> str:
    return reverse("notifications:webhook", kwargs={"org_slug": slug})


# ── Secret enforcement ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWebhookAuth:
    def test_missing_secret_header_is_403(self, api_client, bot_a):
        resp = api_client.post(_webhook_url("osbb-a"), data={}, format="json")
        assert resp.status_code == 403

    def test_wrong_secret_is_403(self, api_client, bot_a):
        resp = api_client.post(
            _webhook_url("osbb-a"),
            data={},
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="wrong",
        )
        assert resp.status_code == 403

    def test_secret_for_another_org_is_403(
        self, api_client, bot_a, bot_b,
    ):
        """Delivering org_b's secret to org_a's slug must fail — the
        secret check is scoped to the URL's org, not looked up globally."""
        resp = api_client.post(
            _webhook_url("osbb-a"),
            data={},
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=bot_b.webhook_secret,
        )
        assert resp.status_code == 403

    def test_unknown_slug_is_403_not_404(self, api_client):
        """We mask 'unknown slug' as the same 403 a bad secret gets —
        so an attacker can't enumerate orgs from the error code."""
        resp = api_client.post(
            _webhook_url("does-not-exist"),
            data={},
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="anything",
        )
        assert resp.status_code == 403

    def test_inactive_bot_is_403(self, api_client, bot_a):
        bot_a.is_active = False
        bot_a.save(update_fields=["is_active"])
        resp = api_client.post(
            _webhook_url("osbb-a"),
            data={},
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=bot_a.webhook_secret,
        )
        assert resp.status_code == 403


# ── Happy path + dispatch ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestWebhookDispatch:
    def test_valid_secret_returns_200_and_dispatches(
        self, api_client, bot_a,
    ):
        update = {
            "message": {
                "chat": {"id": 42},
                "text": "/start",
            },
        }
        with patch(
            "apps.notifications.views.handle_webhook_update",
        ) as mock_handler, patch(
            "apps.notifications.utils.send_message_sync",
        ) as mock_send:
            # Handler returns a reply; the view should forward it via send.
            from apps.notifications.update_handlers import (
                HandlerResult,
                MSG_START_WELCOME,
            )
            mock_handler.return_value = HandlerResult(MSG_START_WELCOME)

            resp = api_client.post(
                _webhook_url("osbb-a"),
                data=update,
                format="json",
                HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=bot_a.webhook_secret,
            )

        assert resp.status_code == 200
        # Dispatched with *this* bot, not another.
        mock_handler.assert_called_once()
        assert mock_handler.call_args.args[0].pk == bot_a.pk
        # Reply was sent back over Telegram with the bot's own token.
        mock_send.assert_called_once_with(
            42, MSG_START_WELCOME, "123:AAE-alpha",
        )

    def test_handler_returns_none_means_no_reply_sent(
        self, api_client, bot_a,
    ):
        """Non-command updates (plain chatter, edits, callbacks) leave
        the handler returning None. The view must 200 and send nothing."""
        with patch(
            "apps.notifications.views.handle_webhook_update",
            return_value=None,
        ), patch(
            "apps.notifications.utils.send_message_sync",
        ) as mock_send:
            resp = api_client.post(
                _webhook_url("osbb-a"),
                data={"message": {"chat": {"id": 42}, "text": "hi"}},
                format="json",
                HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=bot_a.webhook_secret,
            )
        assert resp.status_code == 200
        mock_send.assert_not_called()

    def test_handler_crash_returns_200_still(self, api_client, bot_a):
        """An exception inside the handler mustn't leak a 500 to
        Telegram — Telegram will retry 500s forever, building up load."""
        with patch(
            "apps.notifications.views.handle_webhook_update",
            side_effect=RuntimeError("boom"),
        ):
            resp = api_client.post(
                _webhook_url("osbb-a"),
                data={"message": {"chat": {"id": 42}, "text": "/start"}},
                format="json",
                HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=bot_a.webhook_secret,
            )
        assert resp.status_code == 200

    def test_send_failure_does_not_break_response(
        self, api_client, bot_a,
    ):
        """Handler succeeds but the outbound reply fails (network blip,
        Telegram rate-limited). We still 200 — the user can /start again
        and retries on *our* side shouldn't pile up on Telegram."""
        from apps.notifications.update_handlers import HandlerResult

        with patch(
            "apps.notifications.views.handle_webhook_update",
            return_value=HandlerResult("hi"),
        ), patch(
            "apps.notifications.utils.send_message_sync",
            side_effect=RuntimeError("network down"),
        ):
            resp = api_client.post(
                _webhook_url("osbb-a"),
                data={"message": {"chat": {"id": 42}, "text": "/start"}},
                format="json",
                HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=bot_a.webhook_secret,
            )
        assert resp.status_code == 200
