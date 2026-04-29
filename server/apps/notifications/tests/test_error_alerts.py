"""TDD for TelegramErrorHandler (PR-9).

Covers the runtime side of the error-alerts pipeline:
- pure helpers (fingerprint, traceback trim, request summary, format)
- handler.emit (dispatch + dedup + no-op + must-not-raise)
- the Celery task that actually POSTs to Telegram

All Telegram I/O is mocked — no real HTTP traffic.
"""
from __future__ import annotations

import logging
import sys
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from rest_framework.test import APIRequestFactory

from apps.notifications.error_alerts import (
    TelegramErrorHandler,
    _fingerprint,
    _format_traceback,
    _safe_request_summary,
    format_message,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def alerts_enabled(settings):
    settings.ERROR_ALERTS_TG_BOT_TOKEN = "fake-token-abc"
    settings.ERROR_ALERTS_TG_CHAT_ID = "-1001234567890"


@pytest.fixture
def factory():
    return APIRequestFactory()


def _make_record(
    *,
    exc=None,
    msg="oops",
    path="/api/v1/issues/",
    user_id=None,
    factory=None,
):
    record = logging.LogRecord(
        name="django.request",
        level=logging.ERROR,
        pathname="x.py",
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    if exc is not None:
        try:
            raise exc
        except Exception:
            record.exc_info = sys.exc_info()
    if path is not None and factory is not None:
        request = factory.get(path)
        if user_id is not None:
            class _U:
                is_authenticated = True
                id = user_id
                pk = user_id
                email = "secret@should.not.leak"
            request.user = _U()
        record.request = request
    return record


# ── Pure helpers ─────────────────────────────────────────────────────────────


class TestFingerprint:
    def test_same_exception_same_path_same_fingerprint(self, factory):
        r1 = _make_record(exc=ValueError("boom"), path="/x/", factory=factory)
        r2 = _make_record(exc=ValueError("boom"), path="/x/", factory=factory)
        assert _fingerprint(r1) == _fingerprint(r2)

    def test_different_exception_different_fingerprint(self, factory):
        r1 = _make_record(exc=ValueError("a"), path="/x/", factory=factory)
        r2 = _make_record(exc=KeyError("a"), path="/x/", factory=factory)
        assert _fingerprint(r1) != _fingerprint(r2)

    def test_different_path_different_fingerprint(self, factory):
        r1 = _make_record(exc=ValueError("a"), path="/x/", factory=factory)
        r2 = _make_record(exc=ValueError("a"), path="/y/", factory=factory)
        assert _fingerprint(r1) != _fingerprint(r2)


class TestTracebackTrimming:
    def test_short_traceback_kept_as_is(self):
        try:
            raise RuntimeError("x")
        except Exception:
            tb = _format_traceback(sys.exc_info())
        assert "RuntimeError" in tb
        assert "[truncated]" not in tb

    def test_long_traceback_trimmed_with_marker(self):
        big_exc = RuntimeError("x" * 5000)
        try:
            raise big_exc
        except Exception:
            tb = _format_traceback(sys.exc_info(), max_chars=200)
        assert "[truncated]" in tb
        # Cap is 200 chars + ~30 chars marker overhead
        assert len(tb) < 300

    def test_no_exc_info_returns_empty(self):
        assert _format_traceback(None) == ""
        assert _format_traceback((None, None, None)) == ""


class TestSafeRequestSummary:
    def test_no_body_no_querystring_no_email(self, factory):
        request = factory.post(
            "/api/v1/issues/?secret=hunter2",
            data={"password": "leak"},
            format="json",
        )

        class _U:
            is_authenticated = True
            id = 42
            pk = 42
            email = "leak@nope.com"

        request.user = _U()

        summary = _safe_request_summary(request)
        assert summary["method"] == "POST"
        # path strips querystring
        assert summary["path"] == "/api/v1/issues/"
        assert summary["user_id"] == "42"
        # No body, no querystring, no email anywhere
        joined = "|".join(summary.values())
        assert "hunter2" not in joined
        assert "password" not in joined
        assert "leak" not in joined.lower()

    def test_anonymous_user_no_user_id(self, factory):
        request = factory.get("/x/")
        # Don't set request.user → SimpleLazyObject default; emulate via inline
        class _Anon:
            is_authenticated = False
        request.user = _Anon()
        summary = _safe_request_summary(request)
        assert "user_id" not in summary

    def test_no_request_returns_empty(self):
        assert _safe_request_summary(None) == {}


class TestFormatMessage:
    def test_message_under_4096(self, factory):
        record = _make_record(
            exc=RuntimeError("x" * 8000),
            path="/api/v1/issues/",
            user_id=42,
            factory=factory,
        )
        text = format_message(record)
        assert len(text) <= 4000
        assert "5xx Production Error" in text
        assert "RuntimeError" in text
        assert "id=42" in text
        assert "/api/v1/issues/" in text

    def test_html_escaped(self, factory):
        record = _make_record(
            exc=ValueError("<script>alert(1)</script>"),
            path="/api/v1/<x>/",
            factory=factory,
        )
        text = format_message(record)
        # Raw script tag must NOT appear in the output
        assert "<script>alert(1)</script>" not in text
        assert "&lt;script&gt;" in text

    def test_no_email_in_output(self, factory):
        record = _make_record(
            exc=RuntimeError("boom"),
            path="/x/",
            user_id=42,
            factory=factory,
        )
        text = format_message(record)
        assert "secret@should.not.leak" not in text


# ── Handler behavior ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHandlerEmit:
    def test_no_op_when_token_missing(self, factory, settings):
        settings.ERROR_ALERTS_TG_BOT_TOKEN = ""
        settings.ERROR_ALERTS_TG_CHAT_ID = "-100x"
        h = TelegramErrorHandler()
        record = _make_record(exc=ValueError("x"), factory=factory)
        with patch(
            "apps.notifications.error_alerts.send_telegram_error_alert_task",
        ) as task:
            h.emit(record)
        task.delay.assert_not_called()

    def test_no_op_when_chat_id_missing(self, factory, settings):
        settings.ERROR_ALERTS_TG_BOT_TOKEN = "abc"
        settings.ERROR_ALERTS_TG_CHAT_ID = ""
        h = TelegramErrorHandler()
        record = _make_record(exc=ValueError("x"), factory=factory)
        with patch(
            "apps.notifications.error_alerts.send_telegram_error_alert_task",
        ) as task:
            h.emit(record)
        task.delay.assert_not_called()

    def test_dispatches_celery_task_when_enabled(self, alerts_enabled, factory):
        h = TelegramErrorHandler()
        record = _make_record(exc=ValueError("boom"), factory=factory)
        with patch(
            "apps.notifications.error_alerts.send_telegram_error_alert_task",
        ) as task:
            h.emit(record)
        task.delay.assert_called_once()
        text = task.delay.call_args.args[0]
        assert "ValueError" in text
        assert "boom" in text

    def test_dedup_within_window(self, alerts_enabled, factory):
        h = TelegramErrorHandler(dedup_window_sec=300)
        record = _make_record(exc=ValueError("boom"), factory=factory)
        with patch(
            "apps.notifications.error_alerts.send_telegram_error_alert_task",
        ) as task:
            h.emit(record)
            h.emit(record)
            h.emit(record)
        assert task.delay.call_count == 1

    def test_different_errors_not_deduped(self, alerts_enabled, factory):
        h = TelegramErrorHandler()
        with patch(
            "apps.notifications.error_alerts.send_telegram_error_alert_task",
        ) as task:
            h.emit(_make_record(exc=ValueError("a"), factory=factory))
            h.emit(_make_record(exc=KeyError("b"), factory=factory))
        assert task.delay.call_count == 2

    def test_handler_never_raises(self, alerts_enabled, factory):
        h = TelegramErrorHandler()
        record = _make_record(exc=ValueError("x"), factory=factory)
        # Force the Celery dispatch to fail — handler should swallow.
        with patch(
            "apps.notifications.error_alerts.send_telegram_error_alert_task",
            side_effect=Exception("Celery down"),
        ):
            # Must not raise
            h.emit(record)


# ── Celery task ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSendTask:
    def test_no_op_when_settings_missing(self, settings):
        settings.ERROR_ALERTS_TG_BOT_TOKEN = ""
        settings.ERROR_ALERTS_TG_CHAT_ID = ""
        from apps.notifications.tasks import send_telegram_error_alert_task
        with patch("apps.notifications.tasks.requests.post") as post:
            send_telegram_error_alert_task("x")
        post.assert_not_called()

    def test_posts_to_telegram_when_enabled(self, settings):
        settings.ERROR_ALERTS_TG_BOT_TOKEN = "abc"
        settings.ERROR_ALERTS_TG_CHAT_ID = "-100x"
        from apps.notifications.tasks import send_telegram_error_alert_task
        with patch("apps.notifications.tasks.requests.post") as post:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            post.return_value = mock_response
            send_telegram_error_alert_task("hello")
        post.assert_called_once()
        url = post.call_args.args[0]
        assert "api.telegram.org/botabc/sendMessage" in url
        body = post.call_args.kwargs["json"]
        assert body["chat_id"] == "-100x"
        assert body["text"] == "hello"
        assert body["parse_mode"] == "HTML"
        assert body["disable_web_page_preview"] is True
