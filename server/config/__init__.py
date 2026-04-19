"""Initialise the Celery app alongside Django.

Importing ``celery_app`` here guarantees the Celery application is
created and :func:`celery.Celery.autodiscover_tasks` runs the moment
Django starts — not only when the worker/beat processes explicitly
invoke ``celery -A config.celery_app``.

Why this matters for the Django web process
-------------------------------------------
The Django admin action *"Run selected tasks"* (from
``django_celery_beat``) executes inside the **web** process and looks
the task up via :attr:`celery.current_app.tasks`. Without this import
that registry is empty in gunicorn workers — every admin-triggered
run fails with ``Task "<name>" not found``. The task is still fired
correctly by Beat because the Beat process imports
``config.celery_app`` directly, but operators lose the manual trigger.

Keeping the import here is the canonical Django+Celery layout (see
the Celery documentation's "First steps with Django" tutorial).
"""
from .celery_app import app as celery_app

__all__ = ("celery_app",)
