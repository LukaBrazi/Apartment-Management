from django.db import models
from django.utils.translation import gettext_lazy as _


class SiteSettings(models.Model):
    """Per-organization site settings. Each client (Organization) has their own instance.
    A "default" instance with organization=NULL serves as platform fallback.

    Admin can update hero image, title, subtitle and the CTA button.

    Includes white-label branding, platform identity, and contact
    information.  PR-8 removed the ``current_complex`` FK — ЖК display
    copy lives on the ``complex_name`` / ``complex_address`` /
    ``complex_description`` fields below; building scope is owned by
    ``organization`` exclusively.
    """

    # ─── Organization Scope ──────────────────────────────────────────────────
    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="site_settings",
        null=True,
        blank=True,
        help_text=_("NULL = platform default settings"),
    )

    # ─── Hero Section ────────────────────────────────────────────────────────
    hero_title = models.CharField(
        _("hero title"),
        max_length=200,
        default="Вітаємо в ApartmentOS",
    )
    hero_subtitle = models.CharField(
        _("hero subtitle"),
        max_length=300,
        default="Увійдіть до свого акаунту",
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
        default="Увійти",
    )
    cta_url = models.CharField(
        _("CTA button URL"),
        max_length=200,
        default="/login",
    )

    # ─── Platform Identity ───────────────────────────────────────────────────
    platform_name = models.CharField(
        _("platform name"),
        max_length=100,
        default="ApartmentOS",
        help_text=_("The name of the property management platform (white-label)."),
    )
    platform_tagline = models.CharField(
        _("platform tagline"),
        max_length=200,
        default="Сучасне управління нерухомістю",
        blank=True,
        help_text=_("Short platform tagline or slogan."),
    )
    logo_url = models.CharField(
        _("logo URL"),
        max_length=500,
        blank=True,
        default="",
        help_text=_("External URL to logo or uploaded file path."),
    )
    favicon_url = models.CharField(
        _("favicon URL"),
        max_length=500,
        blank=True,
        default="",
        help_text=_("External URL to favicon or uploaded file path."),
    )

    # ─── Branding Colors ────────────────────────────────────────────────────
    primary_color = models.CharField(
        _("primary color"),
        max_length=7,
        default="#3D7A8A",
        help_text=_("Hex color code for primary branding (e.g., #3D7A8A)."),
    )
    secondary_color = models.CharField(
        _("secondary color"),
        max_length=7,
        default="#1C2B3A",
        help_text=_("Hex color code for secondary branding (e.g., #1C2B3A)."),
    )

    # ─── Complex Identity ────────────────────────────────────────────────────
    complex_name = models.CharField(
        _("complex name"),
        max_length=200,
        blank=True,
        default="",
        help_text=_("Name of the residential complex (ЖК/містечка) — whitelabel display copy."),
    )
    complex_address = models.CharField(
        _("complex address"),
        max_length=500,
        blank=True,
        default="",
        help_text=_("Full address of the complex."),
    )
    complex_description = models.TextField(
        _("complex description"),
        blank=True,
        default="",
        help_text=_("Detailed description of the residential complex."),
    )

    # ─── Support / Contact Information ──────────────────────────────────────
    support_email = models.EmailField(
        _("support email"),
        blank=True,
        default="",
    )
    support_phone = models.CharField(
        _("support phone"),
        max_length=30,
        blank=True,
        default="",
        help_text=_("Phone number for support inquiries."),
    )
    support_hours = models.CharField(
        _("support hours"),
        max_length=100,
        blank=True,
        default="Пн-Пт 09:00-18:00",
        help_text=_("Support availability (e.g., 'Пн-Пт 09:00-18:00')."),
    )
    telegram_url = models.CharField(
        _("telegram URL"),
        max_length=200,
        blank=True,
        default="",
        help_text=_("Link to Telegram channel or bot (e.g., https://t.me/yourbot)."),
    )
    viber_url = models.CharField(
        _("viber URL"),
        max_length=200,
        blank=True,
        default="",
        help_text=_("Link to Viber community or bot."),
    )

    # ─── Footer ─────────────────────────────────────────────────────────────
    footer_text = models.CharField(
        _("footer text"),
        max_length=300,
        blank=True,
        default="",
        help_text=_("Copyright or footer text."),
    )
    terms_url = models.CharField(
        _("terms of service URL"),
        max_length=200,
        blank=True,
        default="",
        help_text=_("Link to terms of service page."),
    )
    privacy_url = models.CharField(
        _("privacy policy URL"),
        max_length=200,
        blank=True,
        default="",
        help_text=_("Link to privacy policy page."),
    )

    # ─── SEO ─────────────────────────────────────────────────────────────────
    meta_title = models.CharField(
        _("meta title"),
        max_length=60,
        blank=True,
        default="",
        help_text=_("HTML meta title tag for SEO."),
    )
    meta_description = models.CharField(
        _("meta description"),
        max_length=160,
        blank=True,
        default="",
        help_text=_("HTML meta description tag for SEO."),
    )

    class Meta:
        verbose_name = _("Site Settings")
        verbose_name_plural = _("Site Settings")

    def __str__(self) -> str:
        if self.organization:
            return f"Settings: {self.organization.name}"
        return "Settings: Platform Default"

    @classmethod
    def get_for_org(cls, organization=None):
        """Get settings for a specific org, fallback to default."""
        if organization:
            obj, _ = cls.objects.get_or_create(organization=organization)
            return obj
        # Return platform default (organization=NULL)
        obj, _ = cls.objects.get_or_create(organization=None)
        return obj

    @classmethod
    def get_default(cls):
        """Platform-level default settings."""
        obj, _ = cls.objects.get_or_create(organization=None)
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


class ContactPerson(models.Model):
    """Contact persons (managers, technicians, emergency services, etc.)
    displayed on the contacts page.

    Scoped to Organization. A NULL organization means platform-level contact.
    """

    class Role(models.TextChoices):
        MANAGER = "manager", _("Управитель")
        TECHNICIAN = "technician", _("Технічний спеціаліст")
        GUARD = "guard", _("Охорона")
        ACCOUNTANT = "accountant", _("Бухгалтерія")
        EMERGENCY = "emergency", _("Аварійна служба")
        OTHER = "other", _("Інше")

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="contact_persons",
        null=True,
        blank=True,
        help_text=_("NULL = platform-level contact"),
    )

    name = models.CharField(
        _("name"),
        max_length=150,
    )
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=Role.choices,
        default=Role.OTHER,
    )
    position = models.CharField(
        _("position"),
        max_length=100,
        blank=True,
        help_text=_("Job title (e.g., 'Головний інженер')."),
    )
    phone = models.CharField(
        _("phone"),
        max_length=30,
        blank=True,
    )
    email = models.EmailField(
        _("email"),
        blank=True,
    )
    telegram = models.CharField(
        _("telegram"),
        max_length=100,
        blank=True,
        help_text=_("Telegram handle or username (without @)."),
    )
    photo = models.ImageField(
        _("photo"),
        upload_to="contacts/",
        blank=True,
        null=True,
    )
    is_emergency = models.BooleanField(
        _("emergency contact"),
        default=False,
        help_text=_("Show in emergency services section."),
    )
    working_hours = models.CharField(
        _("working hours"),
        max_length=100,
        blank=True,
    )
    order = models.PositiveIntegerField(
        _("order"),
        default=0,
        help_text=_("Display order on contacts page."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
    )

    class Meta:
        verbose_name = _("Contact Person")
        verbose_name_plural = _("Contact Persons")
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_role_display()})"
