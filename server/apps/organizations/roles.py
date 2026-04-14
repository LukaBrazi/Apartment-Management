# Imports
from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.organizations.models import OrgRole, OrganizationMembership

User = get_user_model()


# ── Organization Permission Mixin ──────────────────────────────────────────────

class OrgPermissionMixin:
    """OrgPermissionMixin

    Допоміжний клас для перевірки прав доступу організації.

    Methods:
        get_membership(user, org) -> OrganizationMembership | None: Отримати членство користувача.
        get_user_organizations(user) -> QuerySet: Отримати організації користувача.
        is_super_admin(user) -> bool: Перевірити, є ли користувач суперадміністратором.
        is_director_of(user, org) -> bool: Перевірити, є ли користувач директором організації.
        is_admin_of(user, org) -> bool: Перевірити, є ли користувач адміністратором організації.
        is_staff_of(user, org) -> bool: Перевірити, є ли користувач персоналом організації.
        get_highest_role(user, org) -> str | None: Отримати найвищу роль користувача.
    """

    @staticmethod
    def get_membership(user: User, org) -> OrganizationMembership | None:
        """Отримати членство користувача в організації.

        Args:
            user (User): Користувач.
            org (Organization): Організація.

        Returns:
            OrganizationMembership | None: Членство або None.
        """
        try:
            return OrganizationMembership.objects.get(
                user=user,
                organization=org,
            )
        except OrganizationMembership.DoesNotExist:
            return None

    @staticmethod
    def get_user_organizations(user: User) -> QuerySet:
        """Отримати організації, до яких належить користувач.

        Args:
            user (User): Користувач.

        Returns:
            QuerySet: QuerySet організацій.
        """
        from apps.organizations.models import Organization

        return Organization.objects.filter(
            memberships__user=user,
            memberships__is_active=True,
        ).distinct()

    @staticmethod
    def is_super_admin(user: User) -> bool:
        """Перевірити, є ли користувач суперадміністратором.

        Args:
            user (User): Користувач.

        Returns:
            bool: True якщо суперадміністратор, False інакше.
        """
        return user.is_superuser

    @staticmethod
    def is_director_of(user: User, org) -> bool:
        """Перевірити, є ли користувач директором організації.

        Args:
            user (User): Користувач.
            org (Organization): Організація.

        Returns:
            bool: True якщо директор або суперадміністратор, False інакше.
        """
        if user.is_superuser:
            return True

        membership = OrgPermissionMixin.get_membership(user, org)
        if membership is None:
            return False

        return membership.is_director_or_above()

    @staticmethod
    def is_admin_of(user: User, org) -> bool:
        """Перевірити, є ли користувач адміністратором організації.

        Args:
            user (User): Користувач.
            org (Organization): Організація.

        Returns:
            bool: True якщо адміністратор, директор або суперадміністратор, False інакше.
        """
        if user.is_superuser:
            return True

        membership = OrgPermissionMixin.get_membership(user, org)
        if membership is None:
            return False

        return membership.is_admin_or_above()

    @staticmethod
    def is_staff_of(user: User, org) -> bool:
        """Перевірити, є ли користувач персоналом або вище в організації.

        Args:
            user (User): Користувач.
            org (Organization): Організація.

        Returns:
            bool: True якщо персонал або вище, False інакше.
        """
        if user.is_superuser:
            return True

        membership = OrgPermissionMixin.get_membership(user, org)
        if membership is None:
            return False

        return membership.role in [
            OrgRole.SUPER_ADMIN,
            OrgRole.DIRECTOR,
            OrgRole.ADMIN,
            OrgRole.STAFF,
        ]

    @staticmethod
    def get_highest_role(user: User, org) -> str | None:
        """Отримати найвищу роль користувача в організації.

        Args:
            user (User): Користувач.
            org (Organization): Організація.

        Returns:
            str | None: Роль або None.
        """
        membership = OrgPermissionMixin.get_membership(user, org)
        if membership is None:
            return None

        return membership.role
