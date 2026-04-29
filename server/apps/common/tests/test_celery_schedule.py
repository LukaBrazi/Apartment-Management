"""Lock-down: PR-10 health-monitoring schedule entries must stay registered.

If anyone renames a task, swaps the cron, or accidentally drops one of
the three entries during a refactor, these tests fail loud — preserving
the ops contract that:

  * 09:00 and 21:00 Europe/Kyiv → ``daily_health_status_task`` ALWAYS pings
  * top of every hour          → ``hourly_health_monitor_task`` runs

CELERY_TIMEZONE is pinned to Europe/Kyiv (lock-down test in
apps/tests/test_seed_demo_reset_task.py::test_celery_timezone_is_kyiv),
so crontab(hour=9) really does mean 09:00 local — no UTC math here.
"""
from __future__ import annotations

from celery.schedules import crontab
from django.conf import settings


def test_daily_health_morning_scheduled_at_9am():
    schedule = settings.CELERY_BEAT_SCHEDULE
    assert "daily-health-status-morning" in schedule, (
        "CELERY_BEAT_SCHEDULE missing 'daily-health-status-morning'"
    )
    entry = schedule["daily-health-status-morning"]
    assert entry["task"] == "apps.common.tasks.daily_health_status_task"
    cron = entry["schedule"]
    assert isinstance(cron, crontab), f"expected crontab, got {type(cron).__name__}"
    assert 9 in cron.hour, f"expected 9 in cron.hour, got {cron.hour}"
    assert 0 in cron.minute, f"expected 0 in cron.minute, got {cron.minute}"


def test_daily_health_evening_scheduled_at_9pm():
    schedule = settings.CELERY_BEAT_SCHEDULE
    assert "daily-health-status-evening" in schedule, (
        "CELERY_BEAT_SCHEDULE missing 'daily-health-status-evening'"
    )
    entry = schedule["daily-health-status-evening"]
    assert entry["task"] == "apps.common.tasks.daily_health_status_task"
    cron = entry["schedule"]
    assert isinstance(cron, crontab), f"expected crontab, got {type(cron).__name__}"
    assert 21 in cron.hour, f"expected 21 in cron.hour, got {cron.hour}"
    assert 0 in cron.minute, f"expected 0 in cron.minute, got {cron.minute}"


def test_hourly_health_monitor_every_hour():
    schedule = settings.CELERY_BEAT_SCHEDULE
    assert "hourly-health-monitor" in schedule, (
        "CELERY_BEAT_SCHEDULE missing 'hourly-health-monitor'"
    )
    entry = schedule["hourly-health-monitor"]
    assert entry["task"] == "apps.common.tasks.hourly_health_monitor_task"
    cron = entry["schedule"]
    assert isinstance(cron, crontab), f"expected crontab, got {type(cron).__name__}"
    # Fires at :00 every hour. ``hour`` defaults to "every hour" → set of all 24.
    assert 0 in cron.minute, f"expected 0 in cron.minute, got {cron.minute}"
    assert len(cron.hour) == 24, (
        f"expected 'every hour' (24 values), got {cron.hour}"
    )
