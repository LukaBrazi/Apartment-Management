"""Billing app config (PR-13a).

The ``ready()`` hook wires up the post-save signals declared in
``apps.billing.signals`` so the trial subscription auto-creation and
the soft-warn limit checks fire on any code path that creates an
Organization, a Unit, or an OrganizationMembership row.
"""

from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.billing"
    verbose_name = "Billing"

    def ready(self) -> None:  # pragma: no cover — wired at import-time
        from apps.billing import signals  # noqa: F401
