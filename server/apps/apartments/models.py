# Imports
from apps.common.models import TimeStampedModel
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

# Get the user model
User = get_user_model()


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
    # Backward-compat link to legacy Apartment (populated by data migration)
    apartment = models.OneToOneField(
        "apartments.Apartment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unit",
        verbose_name=_("Legacy Apartment"),
    )
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


# ── Legacy Apartment Model (kept for backward compatibility) ────────────────

class Apartment(TimeStampedModel):
    """Apartment

    Apartment class is used to represent an apartment in the database.

    Extends:
        TimeStampedModel

    Attributes:
        unit_number (str): The unit number of the apartment.
        building (str): The building of the apartment.
        floor (int): The floor of the apartment.
        tenant (ForeignKey): The tenant of the apartment.

    Methods:
        __str__(): Return the string representation of the apartment.
    """

    # Attributes
    unit_number = models.CharField(
        max_length=10, verbose_name=_("Unit Number")
    )
    building = models.CharField(max_length=50, verbose_name=_("Building"))
    floor = models.PositiveIntegerField(verbose_name=_("Floor"))
    tenant = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="apartment",
        verbose_name=_("Tenant"),
    )

    class Meta:
        verbose_name = _("Apartment")
        verbose_name_plural = _("Apartments")
        unique_together = [("building", "unit_number")]

    # String Representation
    def __str__(self) -> str:
        """Return the string representation of the apartment.

        Returns:
            str: The string representation of the apartment.
        """

        # Return the string representation
        return f"Unit: {self.unit_number} - Building: {self.building} - Floor: {self.floor}"
