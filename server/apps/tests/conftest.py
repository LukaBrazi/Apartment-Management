"""
Global pytest fixtures for the test suite.

Mocks all Celery task .delay() calls so tests never attempt a real broker
connection (avoids AMQP ACCESS_REFUSED errors on machines where RabbitMQ is
not available or the test environment does not have a valid broker URL).
"""
from unittest.mock import MagicMock, patch

import django
import pytest


@pytest.fixture(autouse=True)
def mock_celery_tasks(settings):
    """
    Patch every Celery task's .delay() / .apply_async() so tests run without
    a broker.  Autouse=True means this fixture is active for every test.
    """
    # Force ALWAYS_EAGER at the Django-settings level
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = False  # don't let task errors kill tests

    task_paths = [
        "apps.notifications.tasks.notify_dispatchers_new_issue",
        "apps.notifications.tasks.notify_tenant_issue_status_changed",
        "apps.notifications.tasks.notify_worker_assigned",
        "apps.notifications.tasks.notify_tenant_pass_status",
        "apps.notifications.tasks.notify_building_tenants_announcement",
        "apps.notifications.tasks.send_telegram_message",
    ]

    # Also patch the references imported into signals module
    signal_task_paths = [
        "apps.notifications.signals.notify_dispatchers_new_issue",
        "apps.notifications.signals.notify_tenant_issue_status_changed",
        "apps.notifications.signals.notify_worker_assigned",
    ]

    patches = []
    for path in task_paths + signal_task_paths:
        try:
            mock_task = MagicMock()
            mock_task.delay = MagicMock(return_value=None)
            mock_task.apply_async = MagicMock(return_value=None)
            p = patch(path, mock_task)
            p.start()
            patches.append(p)
        except Exception:
            pass  # If module not importable, skip silently

    yield

    for p in patches:
        try:
            p.stop()
        except RuntimeError:
            pass
