# Imports
import uuid

from apps.common.models import TimeStampedModel
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

# Get the user model
User = get_user_model()


# ── Organization Type Choices ──────────────────────────────────────────────────

class OrganizationType(models.TextChoices):
    """Типи організацій для управління нерухомістю.

    Інформативне поле — для UI/класифікації.  Логіка прав доступу і
    скоуп квартир працюють через ``Organization`` незалежно від типу.
    """

    HOUSING_COMPLEX = "housing_complex", _("Житловий комплекс")
    COTTAGE_VILLAGE = "cottage_village", _("Котеджне село")
    SINGLE_BUILDING = "single_building", _("Одна будівля")
    MANAGEMENT_COMPANY = "management_company", _("Управляюча компанія")


# ── Organization Role Choices ──────────────────────────────────────────────────

class OrgRole(models.TextChoices):
    """Ролі користувачів в організації"""

    SUPER_ADMIN = "super_admin", _("Суперадміністратор")
    DIRECTOR = "director", _("Директор")
    ADMIN = "admin", _("Адміністратор")
    STAFF = "staff", _("Персонал")
    RESIDENT = "resident", _("Мешканець")


# ── Organization Model ────────────────────────────────────────────────────────

class Organization(TimeStampedModel):
    """Organization Model

    Модель організації для многотенантної системи.

    Extends:
        TimeStampedModel

    Attributes:
        pkid (BigAutoField): Первинний ключ.
        id (UUIDField): Унікальний ідентифікатор UUID.
        name (CharField): Назва організації.
        slug (SlugField): URL-дружелюзний слаг.
        type (CharField): Тип організації (вибір).
        owner (ForeignKey): Власник організації.
        features (JSONField): Функції, що активовані в організації.
        address (CharField): Адреса організації.
        city (CharField): Місто організації.
        description (TextField): Опис організації.
        phone (CharField): Телефон организації.
        email (EmailField): Email організації.
        is_active (BooleanField): Чи є організація активною.

    Meta Class:
        verbose_name (str): Людинозрозуміла назва моделі.
        verbose_name_plural (str): Людинозрозуміла множинна назва моделі.
        ordering (list): Порядок за замовчуванням.

    Methods:
        __str__(): Рядкове представлення моделі.
        is_feature_enabled(feature: str) -> bool: Перевірити, активна ли функція.
        get_enabled_features() -> list: Отримати список активних функцій.
    """

    # Attributes
    pkid = models.BigAutoField(primary_key=True, editable=False)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(_("Organization Name"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True, max_length=255)
    type = models.CharField(
        _("Organization Type"),
        max_length=30,
        choices=OrganizationType.choices,
        default=OrganizationType.HOUSING_COMPLEX,
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_organizations",
        verbose_name=_("Owner"),
    )
    features = models.JSONField(
        _("Features"),
        default=dict,
        help_text=_("Feature flags for this organization"),
    )
    address = models.CharField(
        _("Address"),
        max_length=500,
        blank=True,
        default="",
    )
    city = models.CharField(
        _("City"),
        max_length=100,
        blank=True,
        default="",
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        default="",
    )
    phone = models.CharField(
        _("Phone"),
        max_length=20,
        blank=True,
        default="",
    )
    email = models.EmailField(
        _("Email"),
        blank=True,
        default="",
    )
    is_active = models.BooleanField(
        _("Active"),
        default=True,
        db_index=True,
    )

    # Meta Class
    class Meta:
        """Meta Class

        Attributes:
            verbose_name (str): Людинозрозуміла назва моделі.
            verbose_name_plural (str): Людинозрозуміла множинна назва моделі.
            ordering (list): Порядок за замовчуванням.
        """

        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        ordering = ["-created_at"]

    # String Representation
    def __str__(self) -> str:
        """Return the string representation of the organization.

        Returns:
            str: The string representation of the organization.
        """
        return self.name

    # Save Method
    def save(self, *args, **kwargs) -> None:
        """Save the organization.

        Автоматично генерує слаг з назви, якщо не вказаний.
        """
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    # Feature Flag Methods
    def is_feature_enabled(self, feature: str) -> bool:
        """Перевірити, активна ли функція в організації.

        Args:
            feature (str): Назва функції.

        Returns:
            bool: True якщо функція активна, False інакше.
        """
        return self.features.get(feature, False) is True

    def get_enabled_features(self) -> list:
        """Отримати список активних функцій.

        Returns:
            list: Список назв активних функцій.
        """
        return [
            feature
            for feature, enabled in self.features.items()
            if enabled is True
        ]


# ── Organization Membership Model ──────────────────────────────────────────────

class OrganizationMembership(TimeStampedModel):
    """Organization Membership Model

    Модель членства користувача в організації.

    Extends:
        TimeStampedModel

    Attributes:
        pkid (BigAutoField): Первинний ключ.
        id (UUIDField): Унікальний ідентифікатор UUID.
        user (ForeignKey): Користувач.
        organization (ForeignKey): Організація.
        role (CharField): Роль користувача в організації.
        is_active (BooleanField): Чи є членство активним.
        staff_type (CharField): Тип персоналу (пусто для не-персоналу).
        joined_at (DateTimeField): Коли користувач приєднався.
        invited_by (ForeignKey): Хто запросив користувача.

    Meta Class:
        verbose_name (str): Людинозрозуміла назва моделі.
        verbose_name_plural (str): Людинозрозуміла множинна назва моделі.
        unique_together (list): Унікальні обмеження.
        ordering (list): Порядок за замовчуванням.

    Methods:
        __str__(): Рядкове представлення моделі.
        is_director_or_above() -> bool: Перевірити, є ли користувач директором або вище.
        is_admin_or_above() -> bool: Перевірити, є ли користувач адміністратором або вище.
        can_invite_users() -> bool: Перевірити, може ли користувач запрошувати користувачів.
    """

    # Attributes
    pkid = models.BigAutoField(primary_key=True, editable=False)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
        verbose_name=_("User"),
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("Organization"),
    )
    role = models.CharField(
        _("Role"),
        max_length=30,
        choices=OrgRole.choices,
        default=OrgRole.RESIDENT,
    )
    is_active = models.BooleanField(
        _("Active"),
        default=True,
        db_index=True,
    )
    staff_type = models.CharField(
        _("Staff Type"),
        max_length=100,
        blank=True,
        default="",
        help_text=_("Type of staff (e.g., electrician, plumber)"),
    )
    joined_at = models.DateTimeField(
        _("Joined At"),
        auto_now_add=True,
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_org_invitations",
        verbose_name=_("Invited By"),
    )

    # Meta Class
    class Meta:
        """Meta Class

        Attributes:
            verbose_name (str): Людинозрозуміла назва моделі.
            verbose_name_plural (str): Людинозрозуміла множинна назва моделі.
            unique_together (list): Унікальні обмеження.
            ordering (list): Порядок за замовчуванням.
        """

        verbose_name = _("Organization Membership")
        verbose_name_plural = _("Organization Memberships")
        unique_together = [("user", "organization")]
        ordering = ["-created_at"]

    # String Representation
    def __str__(self) -> str:
        """Return the string representation of the membership.

        Returns:
            str: The string representation of the membership.
        """
        return f"{self.user.full_name} → {self.organization.name} ({self.role})"

    # Permission Check Methods
    def is_director_or_above(self) -> bool:
        """Перевірити, є ли користувач директором або вище.

        Returns:
            bool: True якщо директор або суперадміністратор, False інакше.
        """
        return self.role in [OrgRole.SUPER_ADMIN, OrgRole.DIRECTOR]

    def is_admin_or_above(self) -> bool:
        """Перевірити, є ли користувач адміністратором або вище.

        Returns:
            bool: True якщо адміністратор, директор або суперадміністратор, False інакше.
        """
        return self.role in [
            OrgRole.SUPER_ADMIN,
            OrgRole.DIRECTOR,
            OrgRole.ADMIN,
        ]

    def can_invite_users(self) -> bool:
        """Перевірити, може ли користувач запрошувати користувачів.

        Returns:
            bool: True якщо може запрошувати, False інакше.
        """
        return self.is_admin_or_above()
