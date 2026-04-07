from django.db import models
from django.utils.translation import gettext_lazy as _


class SiteSettings(models.Model):
    """Singleton model — only one row (pk=1) ever exists.

    Admin can update hero image, title, subtitle and the CTA button.
    Holds the active ResidentialComplex (ЖК) for this installation.
    """

    current_complex = models.ForeignKey(
        "apartments.ResidentialComplex",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Active Residential Complex"),
        help_text=_("The ЖК this installation serves. Buildings are scoped to it."),
    )
    hero_title = models.CharField(
        _("hero title"),
        max_length=200,
        default="Welcome to Skandi Apartments",
    )
    hero_subtitle = models.CharField(
        _("hero subtitle"),
        max_length=300,
        default="Are you a new tenant? Or an existing tenant?",
    )
    hero_image = models.ImageField(
        _("hero image"),
        upload_to="site_settings/",
        blank=True,
        null=True,
        help_text=_("Replaces the default background photo on the homepage."),
    )
    cta_text = models.CharField(
        _("CTA button text"),
        max_length=100,
        default="Create Your Account",
    )
    cta_url = models.CharField(
        _("CTA button URL"),
        max_length=200,
        default="/register",
    )

    class Meta:
        verbose_name = _("Site Settings")
        verbose_name_plural = _("Site Settings")

    def __str__(self) -> str:
        return "Site Settings"

    def save(self, *args, **kwargs):
        # Enforce singleton — always pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls) -> "SiteSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SiteLink(models.Model):
    """Navigation / quick-links displayed on the homepage or sidebar."""

    settings = models.ForeignKey(
        SiteSettings,
        on_delete=models.CASCADE,
        related_name="site_links",
        default=1,
    )
    label = models.CharField(_("label"), max_length=100)
    url = models.CharField(
        _("URL"),
        max_length=500,
        help_text=_("Absolute URL (https://…) or internal path (/welcome)."),
    )
    order = models.PositiveSmallIntegerField(_("order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)
    open_in_new_tab = models.BooleanField(_("open in new tab"), default=False)

    class Meta:
        verbose_name = _("Site Link")
        verbose_name_plural = _("Site Links")
        ordering = ["order", "label"]

    def __str__(self) -> str:
        return f"{self.label} → {self.url}"
