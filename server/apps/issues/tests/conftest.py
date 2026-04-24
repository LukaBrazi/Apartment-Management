"""Shared fixtures for apps.issues tests.

Patches Celery `.delay()` calls triggered by Issue signals so tests
don't require a running broker (mirrors the notifications conftest pattern).
"""
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _mock_issue_signal_delays():
    """Suppress all Celery task dispatches fired by Issue/IssueReview signals."""
    patches = [
        patch("apps.notifications.tasks.notify_dispatchers_new_issue.delay"),
        patch("apps.notifications.tasks.notify_tenant_issue_status_changed.delay"),
        patch("apps.notifications.tasks.notify_worker_assigned.delay"),
    ]
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in patches:
            p.stop()
