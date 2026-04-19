# Imports
import os
import uuid
from typing import Dict

from apps.common.models import TimeStampedModel
from autoslug import AutoSlugField
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Avg
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

# Get the user model
User = get_user_model()


# Get the user username
def get_user_username(instance: "Profile") -> str:  # type: ignore
    """Get the user username.

    Args:
        instance (Profile): The profile instance.

    Returns:
        str: The user username.
    """

    # Return the user username
    return instance.user.username


# Upload the avatar
def avatar_upload_to(instance: "Profile", filename: str) -> str:
    """Upload the avatar.

    Args:
        instance (Profile): The profile instance.
        filename (str): The filename.

    Returns:
        str: The avatar path.
    """

    # Get the file extension
    ext = filename.split(".")[-1]

    # Generate a new filename
    filename = f"{uuid.uuid4()}.{ext}"

    # Return the avatar path
    return os.path.join("avatars/", filename)


# Profile Model
class Profile(TimeStampedModel):
    """Profile

    Profile class is used to represent a user profile in the database.

    Extends:
        TimeStampedModel

    Attributes:
        user (OneToOneField): The user the profile belongs to.
        avatar (ImageField): The avatar of the user.
        gender (CharField): The gender of the user. Choices are MALE, FEMALE, and OTHER.
        bio (TextField): The bio of the user.
        occupation (CharField): The occupation of the user. Choices are MASON, CARPENTER, PLUMBER, ROOFER, PAINTER, ELECTRICIAN, HVAC, and TENANT.
        phone_number (PhoneNumberField): The phone number of the user.
        country_of_origin (CountryField): The country of origin of the user.
        city_of_origin (CharField): The city of origin of the user.
        report_count (PositiveIntegerField): The number of reports received by the user.
        reputation (PositiveIntegerField): The reputation of the user.
        slug (AutoSlugField): The slug of the user.

    Methods:
        is_banned: Checks if the user is banned based on the report count.
        update_reputation: Updates the reputation of the user based on the report count.
        save: Overrides the save method to update the reputation before saving.
        get_average_rating: Calculates the average rating received by the user.

    Constants:
        Gender: The options for the gender of the user
        Occupation: The options for the occupation of the user
    """

    # Constants for the gender field
    class Gender(models.TextChoices):
        MALE = ("male", _("Male"))
        FEMALE = ("female", _("Female"))
        OTHER = ("other", _("Other"))

    # Constants for the occupation field
    class Occupation(models.TextChoices):
        MASON = ("mason", _("Mason"))
        CARPENTER = ("carpenter", _("Carpenter"))
        PLUMBER = ("plumber", _("Plumber"))
        ROOFER = ("roofer", _("Roofer"))
        PAINTER = ("painter", _("Painter"))
        ELECTRICIAN = ("electrician", _("Electrician"))
        HVAC = ("hvac", _("HVAC"))
        TENANT = ("tenant", _("Tenant"))
        GUARD = ("guard", _("Guard"))

    # Attributes
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(
        _("Avatar"), upload_to=avatar_upload_to, blank=True, null=True
    )
    gender = models.CharField(
        _("Gender"), choices=Gender.choices, max_length=10, default=Gender.OTHER
    )
    bio = models.TextField(_("Bio"), blank=True, null=True)
    occupation = models.CharField(
        _("Occupation"),
        choices=Occupation.choices,
        max_length=20,
        default=Occupation.TENANT,
    )
    phone_number = PhoneNumberField(
        _("Phone Number"),
        max_length=15,
        default="+91-9204178296",
    )
    country_of_origin = CountryField(_("Country of Origin"), default="IN")
    city_of_origin = models.CharField(
        _("City of Origin"), max_length=180, default="Nagpur"
    )
    unit = models.ForeignKey(
        "apartments.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="residents",
        verbose_name=_("Unit"),
    )
    buildings = models.ManyToManyField(
        "apartments.Building",
        blank=True,
        related_name="staff_profiles",
        verbose_name=_("Managed Buildings"),
        help_text=_("For staff/dispatcher: buildings they manage. Leave empty to manage all buildings."),
    )
    report_count = models.PositiveIntegerField(_("Report Count"), default=0)
    reputation = models.PositiveIntegerField(_("Reputation"), default=100)
    slug = AutoSlugField(
        _("Slug"),
        populate_from=get_user_username,
        unique=True,
        always_update=True,
    )

    # PR-10: primary Unit accessor that prefers the new Residency
    # through-model and falls back to ``self.unit`` during the migration
    # window.  PR-11 will remove the FK entirely — callers must move to
    # this accessor rather than reading ``profile.unit`` directly.
    @property
    def primary_unit(self):
        """Return this profile's canonical Unit.

        Lookup order:
        1. The ``Residency`` row marked ``is_primary=True`` for the
           underlying user — this is the single source of truth once
           PR-11 drops ``Profile.unit``.
        2. Fallback to the legacy ``Profile.unit`` FK, so PR-10 stays
           backward-compatible while the data backfill rolls out.

        The accessor is resilient to a missing ``user`` (unsaved
        profile) and to the ``residencies`` relation being absent on
        older historical states during migrations.
        """

        user = getattr(self, "user", None)
        if user is not None and getattr(user, "pk", None):
            try:
                from apps.apartments.models import Residency

                residency = (
                    Residency.objects.filter(user_id=user.pk, is_primary=True)
                    .select_related("unit__entrance__building")
                    .first()
                )
                if residency is not None:
                    return residency.unit
            except Exception:
                # Historical migration state: the Residency table may
                # not exist yet — fall back silently.
                pass
        return self.unit

    # Property to check if the user is banned
    @property
    def is_banned(self) -> bool:
        """Check if the user is banned based on the report count.

        Returns:
            bool: True if the user is banned, False otherwise.
        """

        # Return True if the report count is greater than or equal to 5
        return self.report_count >= 5

    # Method to update the reputation of the user
    def update_reputation(self) -> None:
        """Update the reputation of the user based on the report count."""

        # Update the reputation based on the report count
        self.reputation = max(0, 100 - self.report_count * 20)

    # Method to save the profile
    def save(self, *args: Dict, **kwargs: Dict) -> None:
        """Override the save method to update the reputation before saving.

        PR-10 also mirrors writes of ``Profile.unit`` into the new
        ``Residency`` through-model so the two sources stay aligned
        while readers are being cut over.  The mirror is best-effort:
        if the ``apartments`` app isn't fully migrated (e.g. during
        tests that tinker with migrations), the save still succeeds.
        """

        # Update the reputation
        self.update_reputation()

        # Return the super save method
        super().save(*args, **kwargs)

        # PR-10: mirror the authoritative FK into Residency so the new
        # readers (Profile.primary_unit, announcements/issues/passes)
        # stay consistent with the admin flow.  Explicit opt-out via
        # ``_skip_residency_mirror`` (used by the PR-10 data migration
        # and tests that want to assert fallback behavior).
        if getattr(self, "_skip_residency_mirror", False):
            return
        if self.user_id and self.unit_id:
            try:
                from apps.apartments.models import Residency

                existing = Residency.objects.filter(
                    user_id=self.user_id, unit_id=self.unit_id
                ).first()
                if existing is None:
                    Residency.objects.create(
                        user_id=self.user_id,
                        unit_id=self.unit_id,
                        role="owner",
                        is_primary=not Residency.objects.filter(
                            user_id=self.user_id, is_primary=True
                        ).exists(),
                    )
                elif not existing.is_primary and not Residency.objects.filter(
                    user_id=self.user_id, is_primary=True
                ).exists():
                    existing.is_primary = True
                    existing.save(update_fields=["is_primary"])
            except Exception:
                # Apartment app not migrated yet (historical migration
                # context) — leave the mirror best-effort.
                pass

    # Method to get the average rating received by the user
    def get_average_rating(self):
        """Calculate the average rating received by the user.

        Returns:
            float: The average rating rounded to 2 decimal places.
        """

        # Get the average rating
        average = self.user.received_ratings.aggregate(Avg("rating"))["rating__avg"]

        # Return the average rating rounded to 2 decimal places
        return round(average, 2) if average is not None else 0.0
