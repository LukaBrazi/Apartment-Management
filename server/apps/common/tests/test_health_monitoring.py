"""TDD for scheduled health monitoring tasks (PR-10 + PR-18).

Two scheduled jobs cover the gap between Railway's per-deploy healthcheck
and "the system is up between deploys":

* ``daily_health_status_task`` — twice-daily ping that ALWAYS fires so
  ops can verify the alert pipeline is actually working (a silent monitor
  is indistinguishable from a broken monitor). PR-18 enriches morning
  runs with a billing digest and evening runs with a security digest.
* ``hourly_health_monitor_task`` — silent on success, alerts on failure
  with hour-bucket dedup so a Beat restart inside the same hour doesn't
  spam the channel, while each new hour CAN re-alert if the issue
  persists.

These tests pin the contract the schedule depends on:
- daily task always calls ``send_telegram_message_task.delay(...)``
- morning runs include a "Білінг" section, evening runs include
  "Безпека" — health checks appear in BOTH
- hourly task only calls it on failure
- hourly task de-dupes within the same hour
- different hour buckets reset the dedup
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.common.tasks import (
    _format_status_message,
    daily_health_status_task,
    hourly_health_monitor_task,
)


def _empty_billing_digest() -> dict:
    return {
        "trial_expiring": [],
        "draft_old_count": 0,
        "draft_old_top": [],
        "overdue_approved_count": 0,
        "overdue_approved_top": [],
        "mrr_uah": Decimal("0"),
    }


def _empty_security_digest() -> dict:
    return {
        "failed_logins": 0,
        "throttle_hits": 0,
        "errors_5xx": 0,
    }


def _morning(year=2026, month=4, day=30, hour=9):
    return datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)


def _evening(year=2026, month=4, day=30, hour=21):
    return datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def mock_send_task():
    """Patch the bound TG sender so tests assert dispatch without HTTP."""
    with patch("apps.common.tasks.send_telegram_message_task") as task:
        yield task


# ── Daily status: always sends ──────────────────────────────────────────────


@pytest.mark.django_db
class TestDailyHealthStatusTask:
    """The daily task is hour-aware (PR-18): morning vs evening branch."""

    def _patch_digests(self, billing=None, security=None):
        """Patch digest builders so DB content doesn't leak into assertions."""
        billing_patcher = patch(
            "apps.billing.digest.build_billing_digest",
            return_value=billing or _empty_billing_digest(),
        )
        security_patcher = patch(
            "apps.common.security_metrics.build_security_digest",
            return_value=security or _empty_security_digest(),
        )
        return billing_patcher, security_patcher

    def test_morning_sends_green_when_all_ok(self, mock_send_task):
        bp, sp = self._patch_digests()
        with bp, sp, patch(
            "apps.common.tasks.run_health_checks",
            return_value={"db": "ok", "cache": "ok"},
        ), patch(
            "apps.common.tasks.dj_timezone.localtime", return_value=_morning(),
        ):
            daily_health_status_task()
        mock_send_task.delay.assert_called_once()
        text = mock_send_task.delay.call_args.args[0]
        assert "🟢" in text
        assert "OK" in text
        assert "✅" in text

    def test_evening_sends_yellow_when_degraded(self, mock_send_task):
        bp, sp = self._patch_digests()
        with bp, sp, patch(
            "apps.common.tasks.run_health_checks",
            return_value={"db": "ok", "cache": "fail"},
        ), patch(
            "apps.common.tasks.dj_timezone.localtime", return_value=_evening(),
        ):
            daily_health_status_task()
        mock_send_task.delay.assert_called_once()
        text = mock_send_task.delay.call_args.args[0]
        assert "🟡" in text
        assert "DEGRADED" in text
        assert "❌" in text

    def test_includes_timestamp(self, mock_send_task):
        bp, sp = self._patch_digests()
        with bp, sp, patch(
            "apps.common.tasks.run_health_checks",
            return_value={"db": "ok", "cache": "ok"},
        ), patch(
            "apps.common.tasks.dj_timezone.localtime", return_value=_morning(),
        ):
            daily_health_status_task()
        text = mock_send_task.delay.call_args.args[0]
        # YYYY-MM-DD pattern in body
        assert re.search(r"\d{4}-\d{2}-\d{2}", text)

    # ── PR-18 enrichment ────────────────────────────────────────────────

    def test_morning_message_includes_billing_section(self, mock_send_task):
        billing = {
            "trial_expiring": [{"name": "AcmeOrg", "days_left": 3}],
            "draft_old_count": 2,
            "draft_old_top": ["INV-2026-000001"],
            "overdue_approved_count": 1,
            "overdue_approved_top": ["INV-2026-000002"],
            "mrr_uah": Decimal("20800.00"),
        }
        bp, sp = self._patch_digests(billing=billing)
        with bp, sp, patch(
            "apps.common.tasks.run_health_checks",
            return_value={"db": "ok", "cache": "ok"},
        ), patch(
            "apps.common.tasks.dj_timezone.localtime", return_value=_morning(),
        ):
            daily_health_status_task()
        text = mock_send_task.delay.call_args.args[0]
        assert "Білінг" in text
        # Billing facts surfaced
        assert "AcmeOrg" in text
        assert "INV-2026-000001" in text
        assert "INV-2026-000002" in text
        assert "MRR" in text

    def test_evening_message_includes_security_section(self, mock_send_task):
        security = {
            "failed_logins": 12,
            "throttle_hits": 3,
            "errors_5xx": 0,
        }
        bp, sp = self._patch_digests(security=security)
        with bp, sp, patch(
            "apps.common.tasks.run_health_checks",
            return_value={"db": "ok", "cache": "ok"},
        ), patch(
            "apps.common.tasks.dj_timezone.localtime", return_value=_evening(),
        ):
            daily_health_status_task()
        text = mock_send_task.delay.call_args.args[0]
        assert "Безпека" in text
        # Security counter values surfaced
        assert "12" in text
        assert "Failed" in text or "logins" in text.lower()

    def test_health_section_present_in_both_morning_and_evening(self, mock_send_task):
        bp, sp = self._patch_digests()
        # Morning
        with bp, sp, patch(
            "apps.common.tasks.run_health_checks",
            return_value={"db": "ok", "cache": "ok"},
        ), patch(
            "apps.common.tasks.dj_timezone.localtime", return_value=_morning(),
        ):
            daily_health_status_task()
        morning_text = mock_send_task.delay.call_args.args[0]
        assert "db" in morning_text
        assert "cache" in morning_text

        mock_send_task.reset_mock()

        # Evening
        bp, sp = self._patch_digests()
        with bp, sp, patch(
            "apps.common.tasks.run_health_checks",
            return_value={"db": "ok", "cache": "ok"},
        ), patch(
            "apps.common.tasks.dj_timezone.localtime", return_value=_evening(),
        ):
            daily_health_status_task()
        evening_text = mock_send_task.delay.call_args.args[0]
        assert "db" in evening_text
        assert "cache" in evening_text

    def test_morning_message_omits_security_section(self, mock_send_task):
        bp, sp = self._patch_digests()
        with bp, sp, patch(
            "apps.common.tasks.run_health_checks",
            return_value={"db": "ok", "cache": "ok"},
        ), patch(
            "apps.common.tasks.dj_timezone.localtime", return_value=_morning(),
        ):
            daily_health_status_task()
        text = mock_send_task.delay.call_args.args[0]
        assert "Безпека" not in text

    def test_evening_message_omits_billing_section(self, mock_send_task):
        bp, sp = self._patch_digests()
        with bp, sp, patch(
            "apps.common.tasks.run_health_checks",
            return_value={"db": "ok", "cache": "ok"},
        ), patch(
            "apps.common.tasks.dj_timezone.localtime", return_value=_evening(),
        ):
            daily_health_status_task()
        text = mock_send_task.delay.call_args.args[0]
        assert "Білінг" not in text

    def test_morning_high_failed_logins_threshold_in_evening(self, mock_send_task):
        """Smoke: high failed-login count surfaces an attention emoji.

        Threshold: >50 failed logins in 24h → prominent marker.
        """
        security = {"failed_logins": 87, "throttle_hits": 0, "errors_5xx": 0}
        bp, sp = self._patch_digests(security=security)
        with bp, sp, patch(
            "apps.common.tasks.run_health_checks",
            return_value={"db": "ok", "cache": "ok"},
        ), patch(
            "apps.common.tasks.dj_timezone.localtime", return_value=_evening(),
        ):
            daily_health_status_task()
        text = mock_send_task.delay.call_args.args[0]
        assert "87" in text
        assert "🚨" in text  # threshold-breach marker


# ── Hourly monitor: silent on healthy, alerts only on failure ───────────────


@pytest.mark.django_db
class TestHourlyHealthMonitorTask:
    def test_silent_when_all_healthy(self, mock_send_task):
        with patch("apps.common.tasks.run_health_checks") as run:
            run.return_value = {"db": "ok", "cache": "ok"}
            hourly_health_monitor_task()
        mock_send_task.delay.assert_not_called()

    def test_alerts_when_db_fails(self, mock_send_task):
        with patch("apps.common.tasks.run_health_checks") as run:
            run.return_value = {"db": "fail", "cache": "ok"}
            hourly_health_monitor_task()
        mock_send_task.delay.assert_called_once()
        text = mock_send_task.delay.call_args.args[0]
        assert "🚨" in text
        assert "Alert" in text

    def test_alerts_when_cache_fails(self, mock_send_task):
        with patch("apps.common.tasks.run_health_checks") as run:
            run.return_value = {"db": "ok", "cache": "fail"}
            hourly_health_monitor_task()
        mock_send_task.delay.assert_called_once()

    def test_dedup_within_same_hour(self, mock_send_task):
        with patch("apps.common.tasks.run_health_checks") as run:
            run.return_value = {"db": "fail", "cache": "ok"}
            hourly_health_monitor_task()
            hourly_health_monitor_task()
            hourly_health_monitor_task()
        # Three runs in same hour → only one alert
        assert mock_send_task.delay.call_count == 1

    def test_alerts_again_after_hour_change(self, mock_send_task):
        with patch("apps.common.tasks.run_health_checks") as run:
            run.return_value = {"db": "fail", "cache": "ok"}

            # First call at hour H
            now1 = datetime(2026, 4, 26, 14, 0, 0, tzinfo=timezone.utc)
            with patch(
                "apps.common.tasks.dj_timezone.localtime", return_value=now1,
            ):
                hourly_health_monitor_task()

            # Second call at hour H+1
            now2 = datetime(2026, 4, 26, 15, 0, 0, tzinfo=timezone.utc)
            with patch(
                "apps.common.tasks.dj_timezone.localtime", return_value=now2,
            ):
                hourly_health_monitor_task()

        # Different hour → fresh fingerprint → both fire
        assert mock_send_task.delay.call_count == 2

    def test_dedup_keyed_by_failure_set_too(self, mock_send_task):
        """If failure set changes within the same hour, emit a new alert.

        Operator value: db-down at 14:00 then cache-also-down at 14:30 is
        a different incident shape and worth re-alerting on.
        """
        now = datetime(2026, 4, 26, 14, 0, 0, tzinfo=timezone.utc)
        with patch("apps.common.tasks.dj_timezone.localtime", return_value=now):
            with patch("apps.common.tasks.run_health_checks") as run:
                run.return_value = {"db": "fail", "cache": "ok"}
                hourly_health_monitor_task()
                run.return_value = {"db": "fail", "cache": "fail"}
                hourly_health_monitor_task()
        assert mock_send_task.delay.call_count == 2


# ── Format helper ───────────────────────────────────────────────────────────


class TestFormatStatusMessage:
    def test_html_escapes_check_names_and_values(self):
        """Defensive escape — even though we control inputs today, lock
        down regression in case future failures surface user-controlled
        text in the message."""
        msg = _format_status_message(
            {"<malicious>": "<script>"},
            "🟢",
            "Header",
        )
        # No raw < > pair from the input survives unescaped
        assert "<script>" not in msg
        assert "<malicious>" not in msg
        # Escaped form is present
        assert "&lt;script&gt;" in msg
        assert "&lt;malicious&gt;" in msg

    def test_includes_header_text(self):
        msg = _format_status_message({"db": "ok"}, "🟢", "ApartmentOS Daily Health — OK")
        assert "ApartmentOS Daily Health — OK" in msg
        assert "🟢" in msg

    def test_uses_green_check_for_ok_red_cross_for_fail(self):
        msg = _format_status_message(
            {"db": "ok", "cache": "fail"}, "🟡", "Header",
        )
        assert "✅" in msg
        assert "❌" in msg
