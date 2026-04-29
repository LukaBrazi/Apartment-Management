"""Custom Django email backend that posts to Resend HTTP API directly (PR-12).

Uses the official ``resend`` Python SDK without an intermediate wrapper
like django-anymail.  Maps Django's ``EmailMessage`` /
``EmailMultiAlternatives`` objects to Resend's API payload.

Configured via:

- ``settings.RESEND_API_KEY`` — required when this backend is active.
- ``settings.DEFAULT_FROM_EMAIL`` — Django standard (env-driven).

Wire-up:

- Direct: ``EMAIL_BACKEND = "apps.common.email_backends.ResendEmailBackend"``
- Async via Celery: keep
  ``EMAIL_BACKEND = "djcelery_email.backends.CeleryEmailBackend"`` and set
  ``CELERY_EMAIL_BACKEND = "apps.common.email_backends.ResendEmailBackend"``
  (this is what production.py does — see PR-12).

Why a custom backend instead of django-anymail
-----------------------------------------------
- No extra dependency layer (anymail is ~10K LOC of generic email
  backends; we exercise only the Resend leg).
- Full control over the payload mapping the day Resend adds new fields.
- Smaller surface for security review (one file, ~120 LOC).

Trade-offs vs anymail
---------------------
- We re-implement attachment encoding (base64), HTML/text alternative
  detection, and cc/bcc/reply_to passthrough manually.  Tests cover
  these mappings — see ``apps/common/tests/test_email_backend.py``.
- No webhooks support out of the box.  If we ever need
  delivered/bounced/opened events, we will add a webhook view in a
  follow-up PR.
"""
from __future__ import annotations

import base64
import logging
from typing import Any, Iterable

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage, EmailMultiAlternatives

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """Send Django ``EmailMessage`` objects via Resend's HTTP API."""

    def __init__(self, fail_silently: bool = False, **kwargs: Any) -> None:
        super().__init__(fail_silently=fail_silently, **kwargs)
        # Lazy-import — avoids hard dependency at settings-load time
        # if Resend isn't installed in dev/CI environments.
        try:
            import resend  # type: ignore

            self._resend = resend
        except ImportError:
            self._resend = None
            if not fail_silently:
                raise

    def send_messages(self, email_messages: Iterable[EmailMessage]) -> int:
        """Send each message via Resend.  Returns count of successful sends.

        Following Django's ``BaseEmailBackend`` contract:

        - Returns ``int`` (count sent), never ``None``.
        - On per-message failure: log + skip (or raise if not
          ``fail_silently``).
        - On config error (no API key): raise (or return ``0`` if
          ``fail_silently``).
        """
        messages = list(email_messages)
        if not messages:
            return 0

        if self._resend is None:
            # Reached only with fail_silently=True (else __init__ raised).
            return 0

        api_key = getattr(settings, "RESEND_API_KEY", "") or ""
        if not api_key:
            if self.fail_silently:
                logger.warning(
                    "ResendEmailBackend: RESEND_API_KEY missing — silent no-op"
                )
                return 0
            raise ValueError(
                "RESEND_API_KEY is not set — cannot send via "
                "ResendEmailBackend. Either set the env var or switch "
                "EMAIL_BACKEND."
            )

        # Set on the SDK module — Resend's client reads it on each call.
        self._resend.api_key = api_key

        sent = 0
        for message in messages:
            try:
                payload = self._build_payload(message)
                self._resend.Emails.send(payload)
                sent += 1
            except Exception as exc:  # noqa: BLE001 — log + decide
                logger.error(
                    "Resend send failed: to=%s subject=%r error=%s",
                    message.to,
                    message.subject,
                    exc,
                )
                if not self.fail_silently:
                    raise
        return sent

    def _build_payload(self, message: EmailMessage) -> dict[str, Any]:
        """Map Django ``EmailMessage`` → Resend API JSON payload.

        Resend payload shape — see
        https://resend.com/docs/api-reference/emails/send-email::

            {
                "from": "name <addr@domain>",
                "to": [str, ...],
                "subject": str,
                "text": str (optional),
                "html": str (optional),
                "cc": [str, ...] (optional),
                "bcc": [str, ...] (optional),
                "reply_to": [str, ...] (optional),
                "attachments": [
                    {"filename": str, "content": base64-str},
                    ...
                ] (optional),
            }
        """
        payload: dict[str, Any] = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": list(message.to),
            "subject": message.subject,
        }

        if message.cc:
            payload["cc"] = list(message.cc)
        if message.bcc:
            payload["bcc"] = list(message.bcc)
        if message.reply_to:
            payload["reply_to"] = list(message.reply_to)

        # Body: detect text vs html based on EmailMultiAlternatives
        # alternatives or single-content messages.
        text_body, html_body = self._extract_bodies(message)
        if text_body is not None:
            payload["text"] = text_body
        if html_body is not None:
            payload["html"] = html_body

        # Attachments — Django stores as (filename, content, mimetype) tuples
        # or as MIMEBase instances; Resend wants base64-encoded content.
        if message.attachments:
            payload["attachments"] = [
                self._encode_attachment(a) for a in message.attachments
            ]

        return payload

    @staticmethod
    def _extract_bodies(
        message: EmailMessage,
    ) -> tuple[str | None, str | None]:
        """Return ``(text_body, html_body)`` from any Django ``EmailMessage``."""
        text_body: str | None = None
        html_body: str | None = None

        # Multi-alternative messages: body is text, alternatives may include html
        if isinstance(message, EmailMultiAlternatives):
            text_body = message.body or None
            for content, mimetype in message.alternatives:
                if mimetype == "text/html":
                    html_body = content
                    break
        else:
            # Plain EmailMessage — body subtype determines kind
            content_subtype = getattr(message, "content_subtype", "plain")
            if content_subtype == "html":
                html_body = message.body
            else:
                text_body = message.body or None

        # Resend rejects fully empty content. If we somehow got nothing,
        # fall back to a single space so the API doesn't 422.
        if text_body is None and html_body is None:
            text_body = " "

        return text_body, html_body

    @staticmethod
    def _encode_attachment(attachment: Any) -> dict[str, str]:
        """Encode a Django attachment to Resend's ``{filename, content}`` dict."""
        if isinstance(attachment, tuple):
            # (filename, content, mimetype)
            filename = attachment[0] or "attachment"
            content = attachment[1] if len(attachment) > 1 else b""
            if isinstance(content, str):
                content_bytes = content.encode("utf-8")
            else:
                content_bytes = content or b""
        else:
            # MIMEBase instance
            filename = attachment.get_filename() or "attachment"
            content_bytes = attachment.get_payload(decode=True) or b""

        return {
            "filename": filename,
            "content": base64.b64encode(content_bytes).decode("ascii"),
        }
