"""Tests for the `seed_demo_reset` Celery task.

The task is wired via Celery Beat (see CELERY_BEAT_SCHEDULE in
config/settings/base.py) to run nightly at 23:00 Europe/Kyiv.

These tests cover:
1. The task delegates to the management command with the right args.
2. The task is registered under the exact name the Beat schedule points to
   — so a rename on one side can't silently break the schedule.
3. The Beat schedule entry exists and has the expected crontab.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from celery.schedules import crontab
from django.conf import settings

from apps.common.tasks import seed_demo_reset


# ── Behavior ────────────────────────────────────────────────────────────────


def test_seed_demo_reset_calls_management_command_with_reset_and_env_passwords():
    """The task must pass both --reset and --passwords-from-env.

    Missing either flag would defeat the purpose of the cron:
    - without --reset the command refuses to drop yesterday's junk,
    - without --passwords-from-env we'd be shipping the dev default
      Demo1234! into prod.
    """
    with patch("apps.common.tasks.call_command") as mock_call:
        seed_demo_reset()

    assert mock_call.call_count == 1
    args, kwargs = mock_call.call_args
    assert args == ("seed_demo",), (
        f"expected call_command('seed_demo', ...), got args={args}"
    )
    assert kwargs.get("reset") is True
    assert kwargs.get("passwords_from_env") is True


def test_seed_demo_reset_propagates_command_errors():
    """If seed_demo raises, the task must raise too.

    Swallowing errors here would mean a silently-broken nightly reset —
    exactly the fail mode Sentry/alerting has to catch.
    """
    from django.core.management.base import CommandError

    with patch(
        "apps.common.tasks.call_command",
        side_effect=CommandError("DEMO_PASSWORD not set"),
    ):
        with pytest.raises(CommandError, match="DEMO_PASSWORD not set"):
            seed_demo_reset()


# ── Registration / wiring ──────────────────────────────────────────────────


def test_task_is_registered_under_expected_name():
    """Celery Beat references the task by string name.

    If someone renames the task but forgets to update CELERY_BEAT_SCHEDULE,
    the beat scheduler would silently keep firing the old name against an
    empty registry — i.e. nothing would ever reset demo data.
    This test fails loud in that case.
    """
    expected_name = "seed_demo_reset"
    assert seed_demo_reset.name == expected_name, (
        f"task registered as {seed_demo_reset.name!r}, "
        f"expected {expected_name!r}"
    )


def test_beat_schedule_has_nightly_entry():
    """The Beat schedule must contain an entry for the nightly reset."""
    schedule = settings.CELERY_BEAT_SCHEDULE
    assert "seed-demo-reset-nightly" in schedule, (
        "CELERY_BEAT_SCHEDULE is missing the 'seed-demo-reset-nightly' entry"
    )

    entry = schedule["seed-demo-reset-nightly"]
    assert entry["task"] == "seed_demo_reset"

    # The schedule should fire at 23:00 local. CELERY_TIMEZONE is pinned to
    # Europe/Kyiv (via TIME_ZONE), so crontab(hour=23, minute=0) is local.
    sched = entry["schedule"]
    assert isinstance(sched, crontab), (
        f"expected crontab schedule, got {type(sched).__name__}"
    )
    # crontab stores hours/minutes as sets of ints
    assert sched.hour == {23}, f"expected hour=23, got {sched.hour}"
    assert sched.minute == {0}, f"expected minute=0, got {sched.minute}"


def test_celery_timezone_is_kyiv():
    """Sanity check: Beat crontab entries assume local Kyiv time.

    If CELERY_TIMEZONE ever changes to UTC or another zone, the hour=23
    crontab above will fire at the wrong wall-clock time. Catch that here.
    """
    assert settings.CELERY_TIMEZONE == "Europe/Kyiv", (
        f"CELERY_TIMEZONE drifted to {settings.CELERY_TIMEZONE!r} — "
        f"the nightly seed reset will fire at the wrong local hour"
    )
