# Imports
from apps.common.models import TimeStampedModel
from django.db import models
from django.utils.translation import gettext_lazy as _


# ── Domain models: Building → Entrance → Unit ──────────────────────────────
#
# PR-7 deleted the legacy ``Apartment`` model.  PR-8 deleted the
# ``ResidentialComplex`` (ЖК) model — buildings are now scoped to
# ``Organization`` exclusively, and whitelabel ЖК display copy lives as
# plain text on ``SiteSettings`` (``complex_name``, ``complex_address``,
# ``complex_description``).  The canonical chain is
# Organization → Building → Entrance → Unit, with ``Profile.unit``
# holding the tenant → unit link.


class Building(TimeStampedModel):
    """Physical building (will be shown as 'Будинок' in UI)."""

    name = models.CharField(_("Name"), max_length=100)
    address = models.CharField(_("Address"), max_length=255)
    city = models.CharField(_("City"), max_length=100, blank=True, default="")
    is_active = models.BooleanField(_("Active"), default=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="buildings",
        null=True,
        blank=True,
        help_text=_("Organization that owns this building"),
    )

    class Meta:
        verbose_name = _("Building")
        verbose_name_plural = _("Buildings")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} — {self.address}"


class Entrance(TimeStampedModel):
    """Entrance / staircase of a building (Під'їзд)."""

    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="entrances",
        verbose_name=_("Building"),
    )
    name = models.CharField(_("Name / Number"), max_length=20)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="entrances",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        verbose_name = _("Entrance")
        verbose_name_plural = _("Entrances")
        ordering = ["building", "name"]
        unique_together = [("building", "name")]

    def __str__(self) -> str:
        return f"{self.building.name} / Entrance {self.name}"

    def save(self, *args, **kwargs):
        if self.building_id and not self.organization_id:
            self.organization = self.building.organization
        super().save(*args, **kwargs)


class Unit(TimeStampedModel):
    """Apartment unit inside an entrance (Квартира)."""

    entrance = models.ForeignKey(
        Entrance,
        on_delete=models.CASCADE,
        related_name="units",
        verbose_name=_("Entrance"),
    )
    number = models.CharField(_("Unit Number"), max_length=20)
    floor = models.PositiveIntegerField(_("Floor"), null=True, blank=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="units",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        verbose_name = _("Unit")
        verbose_name_plural = _("Units")
        ordering = ["entrance", "number"]
        unique_together = [("entrance", "number")]

    def __str__(self) -> str:
        return f"Unit {self.number} — {self.entrance}"

    def save(self, *args, **kwargs):
        if self.entrance_id and not self.organization_id:
            self.organization = self.entrance.organization
        super().save(*args, **kwargs)
