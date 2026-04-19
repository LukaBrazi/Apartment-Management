# Imports
from apps.common.models import TimeStampedModel
from django.db import models
from django.utils.translation import gettext_lazy as _


# ── Residential Complex (ЖК) ───────────────────────────────────────────────

class ResidentialComplex(TimeStampedModel):
    """Житловий комплекс (ЖК).

    One app installation = one active ЖК.
    All buildings belong to a complex; the active complex is set in SiteSettings.
    """

    name = models.CharField(_("Name"), max_length=200, help_text=_("e.g. ЖК Сонячний"))
    address = models.CharField(
        _("Address"), max_length=300, blank=True, default="",
        help_text=_("Main address or district of the complex"),
    )
    city = models.CharField(_("City"), max_length=100, blank=True, default="")
    description = models.TextField(_("Description"), blank=True, default="")

    class Meta:
        verbose_name = _("Residential Complex")
        verbose_name_plural = _("Residential Complexes")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


# ── New domain models: Building → Entrance → Unit ──────────────────────────

class Building(TimeStampedModel):
    """Physical building (will be shown as 'Будинок' in UI)."""

    complex = models.ForeignKey(
        ResidentialComplex,
        on_delete=models.CASCADE,
        related_name="buildings",
        verbose_name=_("Residential Complex"),
        null=True,
        blank=True,
        help_text=_("ЖК this building belongs to"),
    )
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
    # PR-7 dropped the ``Unit.apartment`` OneToOne bridge along with the
    # legacy ``Apartment`` model — tenant ownership lives on
    # ``Profile.unit`` now.
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


# PR-7 deleted the legacy ``Apartment`` model.  Its schema survives only
# in migration history (``apartments.0001`` → ``0005``) for replay.  The
# canonical chain is now ResidentialComplex → Building → Entrance → Unit,
# with ``Profile.unit`` holding the tenant→unit link.
