# Imports
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


# Common Config
class CommonConfig(AppConfig):
    """CommonConfig

    CommonConfig class is used to configure the common app.

    Attributes:
        default_auto_field (str): The default auto field to use for models.
        name (str): The name of the app.
        verbose_name (str): The human-readable name of the app.
    """

    # Attributes
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    verbose_name = _("Common")

    def ready(self) -> None:  # pragma: no cover — wired at import-time
        """Wire up app-load signal handlers.

        PR-18 — connect the ``user_login_failed`` receiver so the
        evening TG digest's ``failed_logins`` counter is fed by every
        failed login regardless of the auth surface (admin, DRF, custom).
        """
        from django.contrib.auth.signals import user_login_failed

        from apps.common.security_metrics import record_failed_login

        user_login_failed.connect(
            record_failed_login,
            dispatch_uid="apps.common.security_metrics.record_failed_login",
        )
