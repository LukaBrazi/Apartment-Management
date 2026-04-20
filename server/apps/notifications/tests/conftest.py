"""Shared pytest fixtures for ``apps.notifications`` tests.

Celery runs in eager mode during tests (see ``config/settings/test.py``).
The default broker URL is ``memory://`` but that string isn't a valid
result-backend name in Celery 5 — the first call to ``.delay()`` tries
to import a module called ``memory`` and crashes. The organizations
app dodges this by mocking the signal-triggered ``.delay`` at source.
We do the same here.

Tests in this package still exercise the task *bodies* directly (by
calling e.g. ``notify_dispatchers_new_issue(str(pk))``), which is what
we want — the autouse fixture only neutralises the outer signal hop
that Issue/Pass/Announcement ``save()`` would otherwise trigger. The
inner ``send_telegram_message.delay`` is patched per-test where it
matters.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _mock_signal_triggered_delays():
    patches = [
        patch("apps.notifications.tasks.notify_dispatchers_new_issue.delay"),
        patch("apps.notifications.tasks.notify_tenant_issue_status_changed.delay"),
        patch("apps.notifications.tasks.notify_worker_assigned.delay"),
        patch("apps.notifications.tasks.notify_tenant_pass_status.delay"),
        patch(
            "apps.notifications.tasks.notify_building_tenants_announcement.delay",
        ),
    ]
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in patches:
            p.stop()
