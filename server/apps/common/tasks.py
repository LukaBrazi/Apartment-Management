# Celery tasks for the common app.
#
# `seed_demo_reset` — nightly demo-data reset. Runs on the Celery Beat
# schedule configured in config/settings/base.py CELERY_BEAT_SCHEDULE.
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

import logging

from celery import shared_task
from django.core.management import call_command


logger = logging.getLogger(__name__)


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
    call_command("seed_demo", reset=True, passwords_from_env=True, verbosity=1)
    logger.info("seed_demo_reset: done")
