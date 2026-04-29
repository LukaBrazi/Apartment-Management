"""Billing domain models (PR-13a).

Six models split across three concerns:

* **Catalog** — ``SubscriptionPlan`` (4 plans on the price list) and
  ``AddOn`` (8 catalog add-ons, mix of one-time and recurring).
* **Per-org state** — ``OrganizationSubscription`` (one per Org, with
  trial window) and ``OrganizationAddOn`` (FK to a catalog AddOn OR a
  custom-name+price line for bespoke modules sold to enterprise orgs).
* **Invoicing** — ``Invoice`` (header with FOP-payer snapshot) and
  ``InvoiceLineItem`` (variable list of charges / credits).

Money is always ``Decimal`` — never floats. Prices are stored in
hryvnia (``uah``) per the FOP-3-group "Без ПДВ" tax mode; if we ever
add VAT or multi-currency that's a follow-up PR.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ── SubscriptionPlan ─────────────────────────────────────────────────────────


class SubscriptionPlan(models.Model):
    """Catalog of available subscription plans (Starter, Business, etc).

    ``max_apartments`` and ``max_users`` are soft limits — the billing
    signals emit a Telegram warning when an org exceeds them, but no
    hard block. Set to ``None`` for "unlimited" (Enterprise tier).
    """

    code = models.CharField(_("Code"), max_length=50, unique=True)
    name = models.CharField(_("Name"), max_length=100)
    monthly_price_uah = models.DecimalField(
        _("Monthly price (UAH)"),
        max_digits=10,
        decimal_places=2,
    )
    max_apartments = models.PositiveIntegerField(
        _("Max apartments"),
        null=True,
        blank=True,
        help_text=_("null = unlimited"),
    )
    max_users = models.PositiveIntegerField(
        _("Max users"),
        null=True,
        blank=True,
        help_text=_("null = unlimited"),
    )
    description_uk = models.TextField(_("Description (UK)"), blank=True)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Subscription Plan")
        verbose_name_plural = _("Subscription Plans")
        ordering = ["monthly_price_uah"]

    def __str__(self) -> str:
        # Strip trailing zeros for compact display ("5900" not "5900.00").
        price = self.monthly_price_uah.normalize()
        # Decimal.normalize() can produce scientific notation for whole
        # numbers (e.g. Decimal("5900").normalize() == 5.9E+3); guard
        # against that with a quantize-back when needed.
        if "E" in str(price):
            price = self.monthly_price_uah.quantize(Decimal("1"))
        return f"{self.name} ({price} UAH/міс)"


# ── AddOn ────────────────────────────────────────────────────────────────────


class AddOn(models.Model):
    """Catalog of paid add-ons (SMS, custom domain, training, etc).

    ``billing_type`` distinguishes one-time charges (onboarding fees)
    from recurring monthly charges (SMS, priority support). The
    calculator service uses this flag to decide which invoice the
    addon belongs to.
    """

    BILLING_ONE_TIME = "one_time"
    BILLING_RECURRING = "recurring_monthly"
    BILLING_TYPE_CHOICES = [
        (BILLING_ONE_TIME, _("One-time")),
        (BILLING_RECURRING, _("Monthly recurring")),
    ]

    code = models.CharField(_("Code"), max_length=80, unique=True)
    name_uk = models.CharField(_("Name (UK)"), max_length=200)
    price_uah = models.DecimalField(
        _("Price (UAH)"),
        max_digits=10,
        decimal_places=2,
    )
    billing_type = models.CharField(
        _("Billing type"),
        max_length=30,
        choices=BILLING_TYPE_CHOICES,
    )
    description_uk = models.TextField(_("Description (UK)"), blank=True)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Add-on")
        verbose_name_plural = _("Add-ons")
        ordering = ["billing_type", "price_uah"]

    def __str__(self) -> str:
        price = self.price_uah.normalize()
        if "E" in str(price):
            price = self.price_uah.quantize(Decimal("1"))
        return f"{self.name_uk} ({price} UAH, {self.get_billing_type_display()})"


# ── OrganizationSubscription ─────────────────────────────────────────────────


class OrganizationSubscription(models.Model):
    """Per-org subscription state — one row per Organization.

    The 60-day trial is set up by the post_save signal in
    ``apps.billing.signals``. ``is_in_trial`` is the helper the calculator
    consults to skip charges while the trial window is open.
    """

    BILLING_MONTHLY = "monthly"
    BILLING_ANNUAL = "annual"
    BILLING_PERIOD_CHOICES = [
        (BILLING_MONTHLY, _("Monthly")),
        (BILLING_ANNUAL, _("Annual")),
    ]

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    billing_period = models.CharField(
        _("Billing period"),
        max_length=20,
        choices=BILLING_PERIOD_CHOICES,
        default=BILLING_MONTHLY,
    )
    started_at = models.DateField(_("Started at"))
    next_billing_at = models.DateField(_("Next billing at"))
    trial_ends_at = models.DateField(
        _("Trial ends at"),
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(_("Active"), default=True)
    is_paused = models.BooleanField(_("Paused"), default=False)

    class Meta:
        verbose_name = _("Organization Subscription")
        verbose_name_plural = _("Organization Subscriptions")

    def __str__(self) -> str:
        return f"{self.organization.name} → {self.plan.name}"

    @property
    def is_in_trial(self) -> bool:
        """True iff today's date is on or before ``trial_ends_at``.

        Returns False when the org never had a trial (``trial_ends_at``
        is None) — this lets us re-use the same flag for "never
        trialed, just paying".
        """
        if self.trial_ends_at is None:
            return False
        return timezone.now().date() <= self.trial_ends_at


# ── OrganizationAddOn ────────────────────────────────────────────────────────


class OrganizationAddOn(models.Model):
    """Activated add-on on a specific org.

    Two valid shapes:
        1. ``addon`` FK is set → catalog add-on (price + name come from AddOn).
        2. ``addon`` is None → custom module: ``custom_name`` and
           ``custom_price_monthly_uah`` MUST both be filled. Custom
           modules are always recurring.

    The check constraint enforces "either (1) or (2), never both empty".
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="addons",
    )
    addon = models.ForeignKey(
        AddOn,
        on_delete=models.PROTECT,
        related_name="org_activations",
        null=True,
        blank=True,
        help_text=_(
            "Leave blank for a custom module — fill custom_name and "
            "custom_price_monthly_uah instead."
        ),
    )
    custom_name = models.CharField(
        _("Custom module name"),
        max_length=200,
        blank=True,
    )
    custom_price_monthly_uah = models.DecimalField(
        _("Custom module monthly price (UAH)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    activated_at = models.DateField(_("Activated at"))
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Organization Add-on")
        verbose_name_plural = _("Organization Add-ons")
        constraints = [
            # Either a catalog FK is set OR custom_name+price are filled.
            # ``custom_name__gt=""`` is the SQLite/Postgres-portable way
            # to say "non-empty string" without hitting the
            # ``CharField(blank=True, default="")`` shenanigans.
            models.CheckConstraint(
                check=(
                    models.Q(addon__isnull=False)
                    | (
                        models.Q(custom_name__gt="")
                        & models.Q(custom_price_monthly_uah__isnull=False)
                    )
                ),
                name="orgaddon_either_catalog_or_custom",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization.name} → {self.effective_name}"

    @property
    def is_custom_module(self) -> bool:
        return self.addon_id is None

    @property
    def effective_name(self) -> str:
        if self.is_custom_module:
            return self.custom_name
        return self.addon.name_uk

    @property
    def effective_price(self) -> Decimal:
        if self.is_custom_module:
            return self.custom_price_monthly_uah
        return self.addon.price_uah

    @property
    def is_recurring(self) -> bool:
        if self.is_custom_module:
            # Custom modules are always recurring monthly by design —
            # one-off bespoke work is invoiced as a manual line item,
            # not as an OrganizationAddOn row.
            return True
        return self.addon.billing_type == AddOn.BILLING_RECURRING


# ── Invoice ──────────────────────────────────────────────────────────────────


class Invoice(models.Model):
    """Header row for an invoice. Line items hang off via FK.

    The ``payer_*_snapshot`` fields freeze the FOP details at the
    moment the invoice was created — if the CEO later changes IBAN /
    tax ID in settings, historical invoices keep the old values for
    GAAP-style auditability.
    """

    STATUS_DRAFT = "draft"
    STATUS_REVIEW = "review"
    STATUS_APPROVED = "approved"
    STATUS_PAID = "paid"
    STATUS_OVERDUE = "overdue"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_DRAFT, _("Draft")),
        (STATUS_REVIEW, _("Review")),
        (STATUS_APPROVED, _("Approved")),
        (STATUS_PAID, _("Paid")),
        (STATUS_OVERDUE, _("Overdue")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    invoice_number = models.CharField(
        _("Invoice number"),
        max_length=50,
        unique=True,
        blank=True,
        help_text=_("Auto-generated as INV-YYYY-NNNNNN if left blank."),
    )
    issued_at = models.DateField(_("Issued at"), default=timezone.now)
    due_at = models.DateField(_("Due at"))
    period_start = models.DateField(_("Period start"))
    period_end = models.DateField(_("Period end"))

    subtotal_uah = models.DecimalField(
        _("Subtotal (UAH)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    discount_uah = models.DecimalField(
        _("Discount (UAH)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_uah = models.DecimalField(
        _("Total (UAH)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    note = models.TextField(_("Note"), blank=True)

    # FOP payer snapshot — frozen at invoice creation time.
    payer_name_snapshot = models.CharField(
        _("Payer name (snapshot)"), max_length=200, blank=True,
    )
    payer_tax_id_snapshot = models.CharField(
        _("Payer tax ID (snapshot)"), max_length=50, blank=True,
    )
    payer_iban_snapshot = models.CharField(
        _("Payer IBAN (snapshot)"), max_length=50, blank=True,
    )
    payer_bank_snapshot = models.CharField(
        _("Payer bank (snapshot)"), max_length=200, blank=True,
    )
    payer_tax_note_snapshot = models.TextField(
        _("Payer tax note (snapshot)"), blank=True,
    )

    sent_to_superuser_at = models.DateTimeField(
        _("Sent to superuser at"), null=True, blank=True,
    )
    sent_to_superuser_email = models.EmailField(
        _("Sent to superuser email"), blank=True,
    )

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        ordering = ["-issued_at", "-id"]
        indexes = [
            models.Index(
                fields=["organization", "-issued_at"],
                name="invoice_org_issued_idx",
            ),
            models.Index(
                fields=["status", "-issued_at"],
                name="invoice_status_issued_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.invoice_number or '<unsaved>'} — {self.total_uah} UAH"

    def save(self, *args, **kwargs):
        """Auto-generate invoice_number on first save if not provided.

        Format ``INV-YYYY-NNNNNN`` — year prefix + 6-digit zero-padded
        sequence. The sequence is monotonic per year; the simple "find
        the highest existing number and +1" loop is fine at our scale
        (we'd need 1M invoices/year before this becomes a hot path).
        """
        if not self.invoice_number:
            year = (self.issued_at or timezone.now().date()).year
            prefix = f"INV-{year}-"
            last = (
                Invoice.objects.filter(invoice_number__startswith=prefix)
                .order_by("-id")
                .first()
            )
            seq = 1
            if last and last.invoice_number:
                try:
                    seq = int(last.invoice_number.rsplit("-", 1)[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            self.invoice_number = f"{prefix}{seq:06d}"
        super().save(*args, **kwargs)


# ── InvoiceLineItem ──────────────────────────────────────────────────────────


class InvoiceLineItem(models.Model):
    """One line on an Invoice. ``line_type`` lets us reconstruct the
    breakdown (base / addons / proration / discounts) without parsing
    the description string.
    """

    LINE_TYPES = [
        ("base_subscription", _("Base subscription")),
        ("addon_recurring", _("Recurring add-on")),
        ("addon_one_time", _("One-time add-on")),
        ("custom_module", _("Custom module")),
        ("proration_credit", _("Proration credit (refund unused)")),
        ("proration_charge", _("Proration charge (new plan partial)")),
        ("annual_discount", _("Annual billing discount")),
        ("trial_credit", _("Trial period credit")),
    ]

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    description = models.CharField(_("Description"), max_length=300)
    quantity = models.PositiveIntegerField(_("Quantity"), default=1)
    unit_price_uah = models.DecimalField(
        _("Unit price (UAH)"),
        max_digits=12,
        decimal_places=2,
    )
    total_uah = models.DecimalField(
        _("Total (UAH)"),
        max_digits=12,
        decimal_places=2,
    )
    line_type = models.CharField(
        _("Line type"),
        max_length=30,
        choices=LINE_TYPES,
    )

    class Meta:
        verbose_name = _("Invoice Line Item")
        verbose_name_plural = _("Invoice Line Items")
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.description} ({self.total_uah} UAH)"
