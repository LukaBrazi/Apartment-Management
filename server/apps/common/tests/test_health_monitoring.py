"""TDD for scheduled health monitoring tasks (PR-10).

Two scheduled jobs cover the gap between Railway's per-deploy healthcheck
and "the system is up between deploys":

* ``daily_health_status_task`` — twice-daily ping that ALWAYS fires so
  ops can verify the alert pipeline is actually working (a silent monitor
  is indistinguishable from a broken monitor).
* ``hourly_health_monitor_task`` — silent on success, alerts on failure
  with hour-bucket dedup so a Beat restart inside the same hour doesn't
  spam the channel, while each new hour CAN re-alert if the issue
  persists.

These tests pin the contract the schedule depends on:
- daily task always calls ``send_telegram_message_task.delay(...)``
- hourly task only calls it on failure
- hourly task de-dupes within the same hour
- different hour buckets reset the dedup
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.common.tasks import (
    _format_status_message,
    daily_health_status_task,
    hourly_health_monitor_task,
)


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
    def test_sends_green_message_when_all_ok(self, mock_send_task):
        with patch("apps.common.tasks.run_health_checks") as run:
            run.return_value = {"db": "ok", "cache": "ok"}
            daily_health_status_task()
        mock_send_task.delay.assert_called_once()
        text = mock_send_task.delay.call_args.args[0]
        assert "🟢" in text
        assert "OK" in text
        assert "✅" in text

    def test_sends_yellow_message_when_degraded(self, mock_send_task):
        with patch("apps.common.tasks.run_health_checks") as run:
            run.return_value = {"db": "ok", "cache": "fail"}
            daily_health_status_task()
        mock_send_task.delay.assert_called_once()
        text = mock_send_task.delay.call_args.args[0]
        assert "🟡" in text
        assert "DEGRADED" in text
        assert "❌" in text

    def test_includes_timestamp(self, mock_send_task):
        with patch("apps.common.tasks.run_health_checks") as run:
            run.return_value = {"db": "ok", "cache": "ok"}
            daily_health_status_task()
        text = mock_send_task.delay.call_args.args[0]
        # YYYY-MM-DD pattern in body
        assert re.search(r"\d{4}-\d{2}-\d{2}", text)


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
