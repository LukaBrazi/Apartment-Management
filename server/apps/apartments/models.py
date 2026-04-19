# Imports
from apps.common.models import TimeStampedModel
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


# ── Domain models: Building → Entrance → Unit ──────────────────────────────
#
# PR-7 deleted the legacy ``Apartment`` model.  PR-8 deleted the
# ``ResidentialComplex`` (ЖК) model — buildings are now scoped to
# ``Organization`` exclusively, and whitelabel ЖК display copy lives as
# plain text on ``SiteSettings``.  PR-9 extends the schema:
#
#   * ``Building.type``       — APARTMENT_BUILDING / COTTAGE (informative).
#   * ``Building.total_area`` — optional, used for cottages that have no
#                                per-unit breakdown.
#   * ``Unit.area``           — optional, square-metres of the unit.
#
# It also introduces ``Residency`` — a through-model between user and
# unit so a single resident can own/rent multiple units (apartments or
# cottages) simultaneously.  ``Profile.unit`` is still authoritative in
# PR-9; readers cut over in PR-10, the FK is removed in PR-11.


class BuildingType(models.TextChoices):
    """Тип будинку — інформативне поле, UI/звітність."""

    APARTMENT_BUILDING = "apartment_building", _("Багатоквартирний будинок")
    COTTAGE = "cottage", _("Приватний котедж")


class Building(TimeStampedModel):
    """Physical building (будинок).

    Most buildings are apartment blocks with entrances and units, but the
    schema is homogeneous — a cottage is modelled as a single-entrance,
    single-unit building.  ``total_area`` is optional and meant for
    cottages that do not carry per-unit area.
    """

    name = models.CharField(_("Name"), max_length=100)
    address = models.CharField(_("Address"), max_length=255)
    city = models.CharField(_("City"), max_length=100, blank=True, default="")
    is_active = models.BooleanField(_("Active"), default=True)
    type = models.CharField(
        _("Building Type"),
        max_length=30,
        choices=BuildingType.choices,
        default=BuildingType.APARTMENT_BUILDING,
        help_text=_(
            "Informational classification — does not affect permissions "
            "or scoping."
        ),
    )
    total_area = models.DecimalField(
        _("Total Area (m²)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_(
            "Optional — total footprint, typically used for cottages "
            "that don't carry per-unit area."
        ),
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="buildings",
        null=True,
        blank=True,
        help_text=_("Organization that owns this building"),
    )
    # Demo-scope marker — defense-in-depth for ``seed_demo --reset``. The
    # reset filter matches on ``is_demo=True`` AND the exact demo name
    # constant. A real building that happens to share the demo name stays
    # safe as long as this flag is False.
    is_demo = models.BooleanField(
        _("Demo Building"),
        default=False,
        db_index=True,
        help_text=_(
            "Marks seed-created demo buildings. The nightly reset only "
            "deletes buildings with is_demo=True."
        ),
    )

    class Meta:
        verbose_name = _("Building")
        verbose_name_plural = _("Buildings")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} — {self.address}"

    def clean(self):
        super().clean()
        if self.total_area is not None and self.total_area < 0:
            raise ValidationError(
                {"total_area": _("Total area must be non-negative.")}
            )


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
    area = models.DecimalField(
        _("Area (m²)"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Unit area in square metres."),
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

    def clean(self):
        super().clean()
        if self.area is not None and self.area < 0:
            raise ValidationError({"area": _("Area must be non-negative.")})


# ── Residency (user × unit through-model) ──────────────────────────────────


class ResidencyRole(models.TextChoices):
    """Роль мешканця відносно квартири/котеджу."""

    OWNER = "owner", _("Власник")
    TENANT = "tenant", _("Орендар")
    FAMILY = "family", _("Член родини")


class Residency(TimeStampedModel):
    """A user's relationship with a particular Unit.

    One resident can hold many residencies (multi-unit owners, rentals,
    family members sharing access).  Exactly one residency per user may
    be marked ``is_primary=True`` — this is the unit used as a default
    for issue-creation, notifications, dashboard, etc.

    PR-9 introduces the model but does not yet cut the readers over
    from ``Profile.unit``; that happens in PR-10 with a data backfill.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="residencies",
        verbose_name=_("User"),
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name="residencies",
        verbose_name=_("Unit"),
    )
    role = models.CharField(
        _("Role"),
        max_length=20,
        choices=ResidencyRole.choices,
        default=ResidencyRole.OWNER,
    )
    is_primary = models.BooleanField(
        _("Primary"),
        default=False,
        help_text=_(
            "Exactly one residency per user may be primary — it is "
            "used as the default unit for issues, notifications, etc."
        ),
    )
    start_date = models.DateField(_("Start Date"), null=True, blank=True)
    end_date = models.DateField(_("End Date"), null=True, blank=True)

    class Meta:
        verbose_name = _("Residency")
        verbose_name_plural = _("Residencies")
        ordering = ["-is_primary", "-start_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "unit"],
                name="residency_unique_user_unit",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_primary=True),
                name="residency_one_primary_per_user",
            ),
        ]

    def __str__(self) -> str:
        marker = " ★" if self.is_primary else ""
        return f"{self.user} → {self.unit} ({self.get_role_display()}){marker}"

    def clean(self):
        super().clean()
        if (
            self.start_date
            and self.end_date
            and self.end_date < self.start_date
        ):
            raise ValidationError(
                {"end_date": _("End date must be on or after start date.")}
            )

    def save(self, *args, **kwargs):
        """Atomically demote any other primary residency for this user
        when this row is saved with ``is_primary=True``.

        Guaranteeing the partial-unique invariant through the ORM keeps
        the common ``residency.is_primary = True; residency.save()``
        path ergonomic — callers don't need to remember to clear other
        primaries first.
        """
        if self.is_primary and self.user_id:
            Residency.objects.filter(
                user_id=self.user_id, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
