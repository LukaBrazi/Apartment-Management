"""Tests for ``apps.notifications.telegram_api`` — sync Telegram REST helpers.

These are tight, mock-only tests: we never hit Telegram in CI.  The
admin actions call ``get_me`` / ``set_webhook`` / ``delete_webhook``
and interpret ``TelegramAPIResult`` — so these tests pin down exactly
what each helper returns for happy-path, Telegram-reported failures,
transport errors, and empty-token guardrails.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.notifications.telegram_api import (
    TelegramAPIResult,
    delete_webhook,
    get_me,
    set_webhook,
)


def _mock_response(json_body: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    return resp


class TestGetMe:
    def test_empty_token_short_circuits(self):
        """No HTTP call should be made when the token is empty."""
        with patch("apps.notifications.telegram_api.httpx.post") as post:
            result = get_me("")
        assert isinstance(result, TelegramAPIResult)
        assert result.ok is False
        assert "empty" in result.error.lower()
        post.assert_not_called()

    def test_happy_path_returns_bot_identity(self):
        body = {
            "ok": True,
            "result": {
                "id": 123,
                "is_bot": True,
                "username": "AlphaBot",
                "first_name": "Alpha",
            },
        }
        with patch(
            "apps.notifications.telegram_api.httpx.post",
            return_value=_mock_response(body),
        ) as post:
            result = get_me("TOKEN")

        assert result.ok is True
        assert result.data == body["result"]
        # URL built correctly: /bot<TOKEN>/getMe
        called_url = post.call_args.args[0]
        assert called_url.endswith("/botTOKEN/getMe")

    def test_telegram_reports_not_ok_becomes_error(self):
        body = {
            "ok": False,
            "error_code": 401,
            "description": "Unauthorized",
        }
        with patch(
            "apps.notifications.telegram_api.httpx.post",
            return_value=_mock_response(body, status_code=401),
        ):
            result = get_me("TOKEN")
        assert result.ok is False
        assert result.error == "Unauthorized"

    def test_network_error_wrapped(self):
        with patch(
            "apps.notifications.telegram_api.httpx.post",
            side_effect=httpx.ConnectError("boom"),
        ):
            result = get_me("TOKEN")
        assert result.ok is False
        assert "network error" in result.error.lower()

    def test_non_json_response_wrapped(self):
        resp = MagicMock()
        resp.status_code = 502
        resp.json.side_effect = ValueError("no json")
        with patch(
            "apps.notifications.telegram_api.httpx.post",
            return_value=resp,
        ):
            result = get_me("TOKEN")
        assert result.ok is False
        assert "non-json" in result.error.lower()


class TestSetWebhook:
    def test_passes_expected_payload(self):
        with patch(
            "apps.notifications.telegram_api.httpx.post",
            return_value=_mock_response({"ok": True, "result": True}),
        ) as post:
            result = set_webhook(
                "TOKEN",
                url="https://apartmentos.org/api/v1/notifications/telegram/webhook/demo/",
                secret_token="SECRET",
            )

        assert result.ok is True
        payload = post.call_args.kwargs["json"]
        assert payload["url"].endswith("/webhook/demo/")
        assert payload["secret_token"] == "SECRET"
        # By default we only ask for message updates.
        assert payload["allowed_updates"] == ["message"]

    def test_custom_allowed_updates_honoured(self):
        with patch(
            "apps.notifications.telegram_api.httpx.post",
            return_value=_mock_response({"ok": True, "result": True}),
        ) as post:
            set_webhook(
                "TOKEN", url="https://x/", secret_token="S",
                allowed_updates=["message", "edited_message"],
            )
        assert post.call_args.kwargs["json"]["allowed_updates"] == [
            "message", "edited_message",
        ]

    def test_telegram_error_surfaced(self):
        body = {
            "ok": False,
            "description": "Bad Request: bad webhook: HTTPS url must be provided",
        }
        with patch(
            "apps.notifications.telegram_api.httpx.post",
            return_value=_mock_response(body, status_code=400),
        ):
            result = set_webhook("TOKEN", url="http://x/", secret_token="S")
        assert result.ok is False
        assert "HTTPS" in result.error


class TestDeleteWebhook:
    def test_happy_path(self):
        with patch(
            "apps.notifications.telegram_api.httpx.post",
            return_value=_mock_response({"ok": True, "result": True}),
        ) as post:
            result = delete_webhook("TOKEN")
        assert result.ok is True
        # ``drop_pending_updates`` kept False so we don't silently lose
        # any queued /start attempts mid-rollout.
        assert post.call_args.kwargs["json"] == {"drop_pending_updates": False}
