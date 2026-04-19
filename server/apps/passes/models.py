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
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        related_name="vehicle_passes",
        null=True,
        blank=True,
        help_text=_("Організація, до якої належить цей пропуск"),
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
            models.Index(fields=["organization", "status"], name="pass_org_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Pass for {self.tenant} on {self.visit_date} [{self.status}]"

    def save(self, *args, **kwargs):
        # Model-level safety net for strict multi-tenant scoping.
        #
        # ``VehiclePassListCreateAPIView`` and ``MyVehiclePassListAPIView``
        # both filter on ``organization__in=get_user_organizations(user)``
        # with no fallback — a pass saved without an ``organization`` is
        # invisible to every non-superuser, including its own tenant.
        #
        # A ``Unit`` always belongs to exactly one ``Organization`` (see
        # ``Unit.save`` — org is auto-derived from the building on first
        # save), so when the caller supplies a unit but forgets the org
        # we can derive it unambiguously.  Callers that explicitly set
        # ``organization`` are never overwritten.
        if not self.organization_id and self.unit_id:
            self.organization_id = self.unit.organization_id
        super().save(*args, **kwargs)
