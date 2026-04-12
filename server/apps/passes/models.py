from apps.apartments.models import Unit
from apps.common.models import TimeStampedModel
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class VehiclePass(TimeStampedModel):
    """A pass request left by a tenant so a guard lets a specific car through."""

    class Status(models.TextChoices):
        PENDING = ("pending", _("Pending"))
        CLOSED = ("closed", _("Closed"))

    tenant = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_passes",
        verbose_name=_("Tenant"),
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_passes",
        verbose_name=_("Unit"),
    )
    car_number = models.CharField(
        _("Car Number"), max_length=20, blank=True, default=""
    )
    comment = models.TextField(_("Comment"), blank=True, default="")
    visit_date = models.DateField(_("Visit Date"))
    status = models.CharField(
        _("Status"),
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    closed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_passes",
        verbose_name=_("Closed By"),
    )
    closed_at = models.DateTimeField(_("Closed At"), null=True, blank=True)

    class Meta:
        verbose_name = _("Vehicle Pass")
        verbose_name_plural = _("Vehicle Passes")
        ordering = ["-visit_date", "-created_at"]
        indexes = [
            models.Index(fields=["status"], name="pass_status_idx"),
            models.Index(fields=["tenant", "status"], name="pass_tenant_status_idx"),
            models.Index(fields=["visit_date"], name="pass_visit_date_idx"),
        ]

    def __str__(self) -> str:
        return f"Pass for {self.tenant} on {self.visit_date} [{self.status}]"
