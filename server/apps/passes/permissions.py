from rest_framework.permissions import BasePermission


class IsGuardOrAdmin(BasePermission):
    """Guards (occupation=guard) and staff/admin."""

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        try:
            return user.profile.occupation == "guard"
        except Exception:
            return False


class IsTenant(BasePermission):
    """Tenants only (occupation=tenant)."""

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        try:
            return user.profile.occupation == "tenant"
        except Exception:
            return False
