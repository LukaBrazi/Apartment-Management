"""Tests for ``ResendEmailBackend`` and email-backend wiring (PR-12 — direct SDK).

ApartmentOS sends transactional email through ``djcelery_email`` (the
top-level ``EMAIL_BACKEND``) which puts each message on the Celery
queue.  The worker then resolves the inner ``CELERY_EMAIL_BACKEND``
to actually deliver — historically that was Django's SMTP backend
talking to ``smtp.resend.com``.  That TCP path keeps timing out from
Railway egress, so PR-12 swaps the inner backend for our custom
``apps.common.email_backends.ResendEmailBackend`` (HTTP API:
``api.resend.com`` via the official ``resend`` Python SDK) behind a
``RESEND_API_KEY`` env-var feature flag.

This file covers two layers:

1. **Lock-down** regex tests — ``base.py`` / ``production.py`` /
   ``requirements/base.txt`` reference the right strings, no
   ``django-anymail`` leftovers, SMTP fallback retained.
2. **Backend** unit tests — payload mapping (text/html/multi-alt,
   cc/bcc/reply_to, attachments) and ``send_messages()`` error paths.

Why regex / file-text tests for layer 1 instead of importing
``production.py``: the prod module reads required env vars at
import-time (``DJANGO_SECRET_KEY``, ``DATABASE_URL``, ``REDIS_URL``,
R2 creds, ``TELEGRAM_BOT_ENCRYPTION_KEY``, …) and fails the boot
loud on miss — desired in production, but breaks pytest collection.
Same pattern as ``test_logging_config.py`` and
``test_security_headers.py``.
"""
from __future__ import annotations

import base64
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.mail import EmailMessage, EmailMultiAlternatives

# server/apps/common/tests/test_email_backend.py
#  → server/apps/common/tests → server/apps/common → server/apps → server
#  → server/config/settings/...
SETTINGS_DIR = Path(__file__).resolve().parents[3] / "config" / "settings"
BASE_PATH = SETTINGS_DIR / "base.py"
PROD_PATH = SETTINGS_DIR / "production.py"
REQ_BASE = Path(__file__).resolve().parents[3] / "requirements" / "base.txt"


# ─────────────────────────────────────────────────────────────────────────────
# Lock-down tests — settings + requirements reference the right strings
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def base_text() -> str:
    assert BASE_PATH.exists(), (
        f"Expected base settings at {BASE_PATH} — has the layout moved? "
        "Update apps/common/tests/test_email_backend.py."
    )
    return BASE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def prod_text() -> str:
    assert PROD_PATH.exists(), (
        f"Expected production settings at {PROD_PATH} — has the layout "
        "moved?  Update apps/common/tests/test_email_backend.py."
    )
    return PROD_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def req_text() -> str:
    return REQ_BASE.read_text(encoding="utf-8")


class TestRequirements:
    """``resend`` SDK is pinned, ``django-anymail`` is gone."""

    def test_no_django_anymail_dependency(self, req_text: str) -> None:
        """We chose the direct Resend SDK over django-anymail wrapper."""
        assert not re.search(
            r"^django-anymail",
            req_text,
            flags=re.MULTILINE,
        ), (
            "django-anymail still pinned in requirements/base.txt — "
            "PR-12 v2 uses the official `resend` SDK directly."
        )

    def test_resend_sdk_pinned(self, req_text: str) -> None:
        """``resend`` must be pinned with an explicit version."""
        assert re.search(
            r"^resend==\d+\.\d+(?:\.\d+)?",
            req_text,
            flags=re.MULTILINE,
        ), (
            "resend SDK must be pinned (==x.y[.z]) in "
            "requirements/base.txt — apps.common.email_backends imports it."
        )


class TestBaseSettings:
    """``base.py`` exposes ``RESEND_API_KEY`` and has no anymail leftovers."""

    def test_no_anymail_in_third_party_apps(self, base_text: str) -> None:
        """``anymail`` must NOT be in ``THIRD_PARTY_APPS`` — direct SDK
        doesn't need a Django app registration."""
        match = re.search(
            r"THIRD_PARTY_APPS\s*=\s*\[(.*?)\]",
            base_text,
            flags=re.DOTALL,
        )
        assert match, "THIRD_PARTY_APPS list not found in base.py"
        apps_block = match.group(1)
        assert (
            '"anymail"' not in apps_block and "'anymail'" not in apps_block
        ), (
            'Remove "anymail" from THIRD_PARTY_APPS — PR-12 v2 dropped '
            "django-anymail in favour of the official Resend SDK."
        )

    def test_no_anymail_settings_block(self, base_text: str) -> None:
        """The legacy ``ANYMAIL = {...}`` dict must be gone."""
        assert "ANYMAIL =" not in base_text, (
            "Remove ANYMAIL settings dict from base.py — direct SDK uses "
            "RESEND_API_KEY only, no anymail-specific config block."
        )

    def test_resend_api_key_setting_present(self, base_text: str) -> None:
        """``RESEND_API_KEY`` must be pulled from env in base.py."""
        assert re.search(
            r"RESEND_API_KEY\s*=\s*env(?:\.str)?\(\s*[\"']RESEND_API_KEY[\"']",
            base_text,
        ), (
            "RESEND_API_KEY env-pull must live in base.py so all tiers "
            "can read it (production.py overrides only when needed)."
        )


class TestProductionSettings:
    """``production.py`` uses the conditional Resend / SMTP switch."""

    def test_production_uses_custom_backend_when_api_key_set(
        self, prod_text: str
    ) -> None:
        """The HTTP-API backend string must appear in production.py —
        without it we silently keep SMTP and the Railway timeout bug
        re-emerges."""
        assert "apps.common.email_backends.ResendEmailBackend" in prod_text, (
            "production.py must reference our custom Resend backend "
            "string — PR-12 v2 migration is incomplete."
        )

    def test_production_no_anymail_backend_reference(
        self, prod_text: str
    ) -> None:
        """No leftover ``anymail.backends.resend.EmailBackend`` reference."""
        assert "anymail.backends.resend" not in prod_text, (
            "production.py still references anymail Resend backend — "
            "PR-12 v2 swapped to apps.common.email_backends."
        )

    def test_production_keeps_smtp_fallback(self, prod_text: str) -> None:
        """When ``RESEND_API_KEY`` is absent, fall back to SMTP backend."""
        assert (
            "django.core.mail.backends.smtp.EmailBackend" in prod_text
        ), (
            "production.py must keep the SMTP fallback for the "
            "no-RESEND_API_KEY path — otherwise local migration "
            "windows break the boot."
        )

    def test_production_sets_celery_email_backend(
        self, prod_text: str
    ) -> None:
        """``CELERY_EMAIL_BACKEND`` is the worker-side backend
        ``djcelery_email`` consults inside the queued task."""
        assert re.search(
            r"^\s*CELERY_EMAIL_BACKEND\s*=",
            prod_text,
            flags=re.MULTILINE,
        ), (
            "production.py must assign CELERY_EMAIL_BACKEND — without "
            "it djcelery_email defaults to the global EMAIL_BACKEND "
            "and the Resend swap is bypassed."
        )

    def test_production_reads_resend_api_key_env(
        self, prod_text: str
    ) -> None:
        """``RESEND_API_KEY`` must be read from env with a safe default
        (``""``) so missing env triggers SMTP fallback, not boot fail."""
        pattern = re.compile(
            r"RESEND_API_KEY\s*=\s*env(?:\.str)?\(\s*[\"']RESEND_API_KEY[\"']"
            r"\s*,\s*default\s*=\s*[\"']{2}\s*\)"
        )
        assert pattern.search(prod_text), (
            "production.py must read RESEND_API_KEY via env(...) with "
            'default="" so missing env falls back to SMTP instead '
            "of crashing the boot."
        )

    def test_resend_branch_gated_on_api_key(self, prod_text: str) -> None:
        """The custom Resend backend must be assigned inside an
        ``if RESEND_API_KEY:`` branch — otherwise the backend tries to
        POST to api.resend.com without credentials and every send
        raises."""
        if_match = re.search(
            r"if\s+RESEND_API_KEY\s*:(.*?)(?:^[A-Z_]|\Z)",
            prod_text,
            flags=re.DOTALL | re.MULTILINE,
        )
        assert if_match, (
            "Expected an `if RESEND_API_KEY:` gate around the Resend "
            "backend assignment in production.py."
        )
        guarded_block = if_match.group(1)
        assert (
            "apps.common.email_backends.ResendEmailBackend" in guarded_block
        ), (
            "ResendEmailBackend must live INSIDE the `if RESEND_API_KEY:` "
            "block — otherwise unauthenticated requests hit api.resend.com "
            "and 401."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Backend payload mapping — Django EmailMessage → Resend JSON
# ─────────────────────────────────────────────────────────────────────────────


def _import_backend():
    """Import the backend lazily so even environments without ``resend``
    installed (rare — it's pinned) don't crash test collection."""
    from apps.common.email_backends import ResendEmailBackend

    return ResendEmailBackend


class TestPayloadMapping:
    """Verify Django ``EmailMessage`` → Resend payload mapping."""

    def setup_method(self) -> None:
        # Patch ``resend`` module so we don't depend on the real SDK
        # for the mapping unit tests.
        self.mock_resend = MagicMock()
        self.module_patcher = patch.dict(
            sys.modules, {"resend": self.mock_resend}
        )
        self.module_patcher.start()
        Backend = _import_backend()
        self.backend = Backend()
        # Override the bound module — _import_backend imports the real
        # one when available; we want our mock for these tests.
        self.backend._resend = self.mock_resend

    def teardown_method(self) -> None:
        self.module_patcher.stop()

    def test_basic_text_message(self) -> None:
        msg = EmailMessage(
            subject="Hello",
            body="Plain body",
            from_email="from@example.com",
            to=["to@example.com"],
        )
        payload = self.backend._build_payload(msg)
        assert payload["from"] == "from@example.com"
        assert payload["to"] == ["to@example.com"]
        assert payload["subject"] == "Hello"
        assert payload["text"] == "Plain body"
        assert "html" not in payload

    def test_html_only_message(self) -> None:
        msg = EmailMessage(
            subject="X",
            body="<p>Hi</p>",
            from_email="f@x.com",
            to=["t@x.com"],
        )
        msg.content_subtype = "html"
        payload = self.backend._build_payload(msg)
        assert payload["html"] == "<p>Hi</p>"
        assert "text" not in payload

    def test_multialternative_includes_both_text_and_html(self) -> None:
        msg = EmailMultiAlternatives(
            subject="X",
            body="Plain text version",
            from_email="f@x.com",
            to=["t@x.com"],
        )
        msg.attach_alternative("<p>HTML version</p>", "text/html")
        payload = self.backend._build_payload(msg)
        assert payload["text"] == "Plain text version"
        assert payload["html"] == "<p>HTML version</p>"

    def test_cc_bcc_reply_to_passed_through(self) -> None:
        msg = EmailMessage(
            subject="X",
            body="Y",
            from_email="f@x.com",
            to=["t@x.com"],
            cc=["c1@x.com", "c2@x.com"],
            bcc=["b@x.com"],
            reply_to=["r@x.com"],
        )
        payload = self.backend._build_payload(msg)
        assert payload["cc"] == ["c1@x.com", "c2@x.com"]
        assert payload["bcc"] == ["b@x.com"]
        assert payload["reply_to"] == ["r@x.com"]

    def test_no_cc_means_no_cc_key(self) -> None:
        msg = EmailMessage(
            subject="X", body="Y", from_email="f@x.com", to=["t@x.com"]
        )
        payload = self.backend._build_payload(msg)
        assert "cc" not in payload
        assert "bcc" not in payload
        assert "reply_to" not in payload

    def test_attachment_tuple_encoded_as_base64(self) -> None:
        msg = EmailMessage(
            subject="X",
            body="Y",
            from_email="f@x.com",
            to=["t@x.com"],
        )
        msg.attach("report.pdf", b"\x00\x01\x02PDF", "application/pdf")
        payload = self.backend._build_payload(msg)
        assert "attachments" in payload
        atts = payload["attachments"]
        assert len(atts) == 1
        assert atts[0]["filename"] == "report.pdf"
        decoded = base64.b64decode(atts[0]["content"])
        assert decoded == b"\x00\x01\x02PDF"

    def test_attachment_string_content_encoded(self) -> None:
        msg = EmailMessage(
            subject="X",
            body="Y",
            from_email="f@x.com",
            to=["t@x.com"],
        )
        msg.attach("note.txt", "hello", "text/plain")
        payload = self.backend._build_payload(msg)
        decoded = base64.b64decode(payload["attachments"][0]["content"])
        assert decoded == b"hello"

    def test_empty_body_falls_back_to_space(self) -> None:
        """Resend 422s on empty content; we send a space as guardrail."""
        msg = EmailMessage(
            subject="X", body="", from_email="f@x.com", to=["t@x.com"]
        )
        payload = self.backend._build_payload(msg)
        # text or html present and non-empty
        assert payload.get("text") or payload.get("html")


# ─────────────────────────────────────────────────────────────────────────────
# send_messages() — config + per-message error handling
# ─────────────────────────────────────────────────────────────────────────────


class TestSendMessages:
    """Cover the contract of ``BaseEmailBackend.send_messages``."""

    def setup_method(self) -> None:
        self.mock_resend = MagicMock()
        self.module_patcher = patch.dict(
            sys.modules, {"resend": self.mock_resend}
        )
        self.module_patcher.start()

    def teardown_method(self) -> None:
        self.module_patcher.stop()

    def _backend(self, **kwargs):
        Backend = _import_backend()
        backend = Backend(**kwargs)
        backend._resend = self.mock_resend
        return backend

    def test_no_messages_returns_zero(self, settings) -> None:
        settings.RESEND_API_KEY = "re_test"
        backend = self._backend()
        assert backend.send_messages([]) == 0

    def test_no_api_key_raises_when_not_silent(self, settings) -> None:
        settings.RESEND_API_KEY = ""
        backend = self._backend(fail_silently=False)
        msg = EmailMessage("X", "Y", "f@x.com", ["t@x.com"])
        with pytest.raises(ValueError, match="RESEND_API_KEY"):
            backend.send_messages([msg])

    def test_no_api_key_silent_returns_zero(self, settings) -> None:
        settings.RESEND_API_KEY = ""
        backend = self._backend(fail_silently=True)
        msg = EmailMessage("X", "Y", "f@x.com", ["t@x.com"])
        assert backend.send_messages([msg]) == 0

    def test_successful_send_returns_count(self, settings) -> None:
        settings.RESEND_API_KEY = "re_test"
        self.mock_resend.Emails.send = MagicMock(return_value={"id": "abc"})
        backend = self._backend()
        msgs = [
            EmailMessage("S1", "B1", "f@x.com", ["t1@x.com"]),
            EmailMessage("S2", "B2", "f@x.com", ["t2@x.com"]),
        ]
        assert backend.send_messages(msgs) == 2
        assert self.mock_resend.Emails.send.call_count == 2

    def test_per_message_error_logged_continues_when_silent(
        self, settings, caplog
    ) -> None:
        settings.RESEND_API_KEY = "re_test"
        self.mock_resend.Emails.send = MagicMock(
            side_effect=[Exception("API down"), {"id": "abc"}]
        )
        backend = self._backend(fail_silently=True)
        msgs = [
            EmailMessage("S1", "B1", "f@x.com", ["t1@x.com"]),
            EmailMessage("S2", "B2", "f@x.com", ["t2@x.com"]),
        ]
        with caplog.at_level("ERROR"):
            count = backend.send_messages(msgs)
        assert count == 1  # second one succeeded
        assert any(
            "Resend send failed" in r.message for r in caplog.records
        )

    def test_per_message_error_raises_when_not_silent(
        self, settings
    ) -> None:
        settings.RESEND_API_KEY = "re_test"
        self.mock_resend.Emails.send = MagicMock(
            side_effect=Exception("API down")
        )
        backend = self._backend(fail_silently=False)
        msg = EmailMessage("S", "B", "f@x.com", ["t@x.com"])
        with pytest.raises(Exception, match="API down"):
            backend.send_messages([msg])
