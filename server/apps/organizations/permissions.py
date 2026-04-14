# Imports
from rest_framework import permissions

from apps.organizations.roles import OrgPermissionMixin


# ── Superuser Permission ───────────────────────────────────────────────────────

class IsSuperAdmin(permissions.BasePermission):
    """IsSuperAdmin

    Дозволити доступ тільки суперадміністраторам.

    Methods:
        has_permission: Перевірити, чи дозволено
    """

    message = "Only superusers can access this resource."

    def has_permission(self, request, view) -> bool:
        """Перевірити, чи дозволено доступ.

        Args:
            request: HTTP request.
            view: DRF view.

        Returns:
            bool: True если доступ дозволено, False інакше.
        """
        return request.user and request.user.is_authenticated and request.user.is_superuser


# ── Director or Above Permission ───────────────────────────────────────────────

class IsDirectorOrAbove(permissions.BasePermission):
    """IsDirectorOrAbove

    Дозволити доступ суперадміністраторам та директорам організації.

    Methods:
        has_permission: Перевірити, чи дозволено
    """

    message = "Only directors and superusers can access this resource."

    def has_permission(self, request, view) -> bool:
        """Перевірити, чи дозволено доступ.

        Args:
            request: HTTP request.
            view: DRF view.

        Returns:
            bool: True якщо доступ дозволено, False інакше.
        """
        if not (request.user and request.user.is_authenticated):
            return False

        # Для списків - дозволити доступ
        if request.method == "GET" and hasattr(view, "list"):
            return True

        # Для операцій над конкретною організацією
        org = self._get_organization(view)
        if org:
            return OrgPermissionMixin.is_director_of(request.user, org)

        return False

    def _get_organization(self, view):
        """Отримати організацію з view."""
        if hasattr(view, "kwargs") and "organization_id" in view.kwargs:
            from apps.organizations.models import Organization

            try:
                return Organization.objects.get(id=view.kwargs["organization_id"])
            except Organization.DoesNotExist:
                return None
        return None


# ── Admin or Above Permission ──────────────────────────────────────────────────

class IsAdminOrAbove(permissions.BasePermission):
    """IsAdminOrAbove

    Дозволити доступ суперадміністраторам, директорам та адміністраторам організації.

    Methods:
        has_permission: Перевірити, чи дозволено
    """

    message = "Only admins and above can access this resource."

    def has_permission(self, request, view) -> bool:
        """Перевірити, чи дозволено доступ.

        Args:
            request: HTTP request.
            view: DRF view.

        Returns:
            bool: True якщо доступ дозволено, False інакше.
        """
        if not (request.user and request.user.is_authenticated):
            return False

        # Для списків - дозволити доступ
        if request.method == "GET" and hasattr(view, "list"):
            return True

        # Для операцій над конкретною організацією
        org = self._get_organization(view)
        if org:
            return OrgPermissionMixin.is_admin_of(request.user, org)

        return False

    def _get_organization(self, view):
        """Отримати організацію з view."""
        if hasattr(view, "kwargs") and "organization_id" in view.kwargs:
            from apps.organizations.models import Organization

            try:
                return Organization.objects.get(id=view.kwargs["organization_id"])
            except Organization.DoesNotExist:
                return None
        return None


# ── Staff or Above Permission ──────────────────────────────────────────────────

class IsStaffOrAbove(permissions.BasePermission):
    """IsStaffOrAbove

    Дозволити доступ суперадміністраторам та членам організації.

    Methods:
        has_permission: Перевірити, чи дозволено
    """

    message = "Only members of this organization can access this resource."

    def has_permission(self, request, view) -> bool:
        """Перевірити, чи дозволено доступ.

        Args:
            request: HTTP request.
            view: DRF view.

        Returns:
            bool: True якщо доступ дозволено, False інакше.
        """
        if not (request.user and request.user.is_authenticated):
            return False

        org = self._get_organization(view)
        if org:
            return OrgPermissionMixin.is_staff_of(request.user, org)

        return False

    def _get_organization(self, view):
        """Отримати організацію з view."""
        if hasattr(view, "kwargs") and "organization_id" in view.kwargs:
            from apps.organizations.models import Organization

            try:
                return Organization.objects.get(id=view.kwargs["organization_id"])
            except Organization.DoesNotExist:
                return None
        return None


# ── Resident in Organization Permission ───────────────────────────────────────

class IsResidentInOrg(permissions.BasePermission):
    """IsResidentInOrg

    Дозволити доступ резидентам та членам організації.

    Methods:
        has_permission: Перевірити, чи дозволено
    """

    message = "You must be a member of this organization."

    def has_permission(self, request, view) -> bool:
        """Перевірити, чи дозволено доступ.

        Args:
            request: HTTP request.
            view: DRF view.

        Returns:
            bool: True якщо доступ дозволено, False інакше.
        """
        if not (request.user and request.user.is_authenticated):
            return False

        org = self._get_organization(view)
        if org:
            membership = OrgPermissionMixin.get_membership(request.user, org)
            return membership is not None and membership.is_active

        return False

    def _get_organization(self, view):
        """Отримати організацію з view."""
        if hasattr(view, "kwargs") and "organization_id" in view.kwargs:
            from apps.organizations.models import Organization

            try:
                return Organization.objects.get(id=view.kwargs["organization_id"])
            except Organization.DoesNotExist:
                return None
        return None


# ── Organization Data Isolation Mixin ──────────────────────────────────────────

class OrgDataIsolationMixin:
    """OrgDataIsolationMixin

    Допоміжний клас для фільтрації даних за організаціями користувача.

    Methods:
        get_queryset: Фільтрувати QuerySet
    """

    def get_queryset(self):
        """Фільтрувати QuerySet за організаціями користувача.

        Returns:
            QuerySet: Відфільтрований QuerySet.
        """
        # Для суперадміністраторів - повернути весь QuerySet
        if self.request.user.is_superuser:
            return super().get_queryset()

        # Отримати організації користувача
        user_orgs = OrgPermissionMixin.get_user_organizations(self.request.user)

        # Фільтрувати QuerySet
        base_qs = super().get_queryset()

        # Якщо є поле organization_id
        if hasattr(base_qs.model, "organization"):
            return base_qs.filter(organization__in=user_orgs)

        # Якщо є поле organization (ForeignKey)
        if hasattr(base_qs.model, "organization_id"):
            return base_qs.filter(organization_id__in=user_orgs)

        # Для моделі Organization
        if hasattr(base_qs.model, "memberships"):
            return base_qs.filter(memberships__user=self.request.user)

        return base_qs
