# Celery tasks for the common app.
#
# `seed_demo_reset` — nightly demo-data reset. Runs on the Celery Beat
# schedule configured in config/settings/base.py CELERY_BEAT_SCHEDULE.
#
# `daily_health_status_task` / `hourly_health_monitor_task` (PR-10) —
# scheduled health monitoring. Both reuse `apps.common.health.run_health_checks`
# so the Telegram pings see the SAME view of healthy/unhealthy as the
# Railway probe at /api/v1/health/.
#
# Why Celery Beat and not a K8s CronJob / Railway cron:
# - Celery is already deployed (worker + beat services on Railway).
# - CELERY_TIMEZONE is pinned to Europe/Kyiv, so a `crontab(hour=23)`
#   entry naturally lands at 23:00 local time year-round — DST handled
#   by Celery, no manual flips twice a year.
# - DatabaseScheduler stores active schedules in the DB, so product/ops
#   can toggle the reset from Django Admin without a redeploy.
#
# The K8s manifest at infra/k8s/demo-reset-cronjob.yaml is kept as a
# reference for a future migration off Railway.
from __future__ import annotations

import html
import io
import logging
import re

from celery import shared_task
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone as dj_timezone


logger = logging.getLogger(__name__)

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


class _LoggerWriter(io.TextIOBase):
    """Redirect management-command stdout to logger.info.

    Celery captures raw sys.stdout and emits every line at WARNING level,
    which makes routine seed output look alarming in production logs.
    Passing this writer to call_command keeps seed progress at INFO.
    """

    def write(self, message: str) -> int:
        clean = _ANSI_ESCAPE.sub("", message).rstrip()
        if clean:
            logger.info(clean)
        return len(message)


@shared_task(
    name="seed_demo_reset",
    # seed_demo takes ≤60s on a warm DB per DEMO_SEED_PLAN.md §10.5.
    # Give it a hard 5-minute ceiling and a 3-minute soft deadline so
    # SIGTERM lands before SIGKILL if something stalls.
    time_limit=300,
    soft_time_limit=180,
    # Don't re-queue on worker death: a seed mid-flight that gets
    # restarted twice could cascade. Rather let tomorrow's run recover.
    acks_late=False,
    # No automatic retries — if the reset fails, page a human and look.
    # The command already wraps everything in a single transaction, so
    # a failure leaves the previous day's demo intact.
    autoretry_for=(),
    max_retries=0,
)
def seed_demo_reset() -> None:
    """Run `manage.py seed_demo --reset --passwords-from-env`.

    Invoked by Celery Beat every night at 23:00 Europe/Kyiv. Requires
    the ``DEMO_PASSWORD`` env var to be set on the worker (>= 8 chars);
    ``seed_demo`` raises ``CommandError`` otherwise.

    Expected duration: 5–30 seconds on warm DB.
    """
    logger.info("seed_demo_reset: starting nightly demo reset")
    call_command("seed_demo", reset=True, passwords_from_env=True, verbosity=1, stdout=_LoggerWriter())
    logger.info("seed_demo_reset: done")


# ── Scheduled health monitoring (PR-10) ─────────────────────────────────────
#
# Two scheduled jobs cover the gap between Railway's per-deploy healthcheck
# and "the system is up between deploys":
#
#   * daily_health_status_task   — 09:00 + 21:00 Europe/Kyiv. ALWAYS sends
#                                   so ops can verify the alert pipeline is
#                                   actually working (a silent monitor is
#                                   indistinguishable from a broken one).
#   * hourly_health_monitor_task — top of every hour. SILENT on success,
#                                   alerts on failure. Hour-bucket dedup
#                                   means a Beat restart inside the same
#                                   hour doesn't spam the channel, while
#                                   each new hour can re-alert if the
#                                   problem persists.
#
# Both reuse run_health_checks() from apps.common.health so the Telegram
# pings reflect the EXACT same view of healthy/unhealthy as /api/v1/health/.
# Both dispatch via apps.notifications.tasks.send_telegram_message_task —
# the existing PR-9 TG channel (ERROR_ALERTS_TG_* env vars) is reused.
#
# Imports of run_health_checks and send_telegram_message_task happen at
# module level here (resolved lazily by name in helper) — see the bound
# names below for test patchability.
from apps.common.health import run_health_checks  # noqa: E402
from apps.notifications.tasks import send_telegram_message_task  # noqa: E402


def _format_status_message(
    checks: dict[str, str], header_icon: str, header_text: str,
) -> str:
    """Build an HTML-safe Telegram message body (works healthy + degraded).

    All inputs are HTML-escaped — even though our caller controls them
    today, defensive escaping locks down a regression class where a
    future check name surfaces user-controlled text and Telegram's
    parse_mode=HTML would otherwise render it as markup.
    """
    lines = [
        f"{header_icon} <b>{html.escape(header_text)}</b>",
        "",
        f"<b>Час:</b> {dj_timezone.localtime().strftime('%Y-%m-%d %H:%M %Z')}",
        "",
    ]
    for name, val in checks.items():
        emoji = "✅" if val == "ok" else "❌"
        lines.append(
            f"{emoji} <b>{html.escape(name)}</b>: {html.escape(val)}",
        )
    return "\n".join(lines)


@shared_task
def daily_health_status_task() -> None:
    """Twice-daily health ping. ALWAYS sends regardless of state.

    Scheduled at 09:00 and 21:00 Europe/Kyiv via CELERY_BEAT_SCHEDULE.
    The "always sends" semantics is intentional: if the channel goes
    silent for >24h, ops know the monitor itself is broken — same alarm
    surface either way.
    """
    checks = run_health_checks()
    all_ok = all(v == "ok" for v in checks.values())

    if all_ok:
        text = _format_status_message(
            checks, "🟢", "ApartmentOS Daily Health — OK",
        )
    else:
        text = _format_status_message(
            checks, "🟡", "ApartmentOS Daily Health — DEGRADED",
        )

    send_telegram_message_task.delay(text)


@shared_task
def hourly_health_monitor_task() -> None:
    """Hourly probe — sends ONLY if any check failed.

    Dedup via cache key that includes the current hour timestamp AND the
    sorted set of failed check names:

      * Same hour + same failures → suppressed (Beat restart no-op).
      * New hour + same failures  → fresh fingerprint → re-alerts so a
        prolonged outage stays visible.
      * Same hour + DIFFERENT failures → fresh fingerprint → re-alerts
        because the incident shape changed (e.g. db-only → db+cache).

    TTL of 3600s naturally rotates with the hour bucket; if the cache
    backend evicts the key sooner under memory pressure, worst case is
    a duplicate ping (acceptable failure mode).
    """
    checks = run_health_checks()
    failures = sorted(name for name, val in checks.items() if val == "fail")

    if not failures:
        return  # Silent on healthy — that's the whole point of the hourly probe.

    now = dj_timezone.localtime()
    hour_bucket = now.strftime("%Y%m%d%H")
    fingerprint = f"health_monitor_alert:{hour_bucket}:{':'.join(failures)}"
    if cache.get(fingerprint):
        logger.info(
            "Hourly health alert deduplicated for %s at %s",
            failures,
            hour_bucket,
        )
        return
    cache.set(fingerprint, "1", 3600)  # 1h TTL — rotates naturally with bucket

    text = _format_status_message(
        checks, "🚨", "ApartmentOS Health Alert",
    )
    send_telegram_message_task.delay(text)
