"""
Утиліти для автоматичного витягування організації користувача.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError


def get_user_primary_organization(user):
    """Return the user's first active OrganizationMembership.

    Superusers are not bound to a single org and always return ``None``.
    A regular user without any active membership also returns ``None``;
    callers are responsible for handling that case (typically by
    rejecting the request via the IsAuthenticated + scoped-queryset
    pattern, never by silently widening visibility).
    """
    if user.is_superuser:
        return None

    membership = user.organization_memberships.filter(is_active=True).select_related("organization").first()
    return membership.organization if membership else None


def get_user_organizations(user):
    """Повертає QuerySet всіх активних організацій користувача."""
    if user.is_superuser:
        from apps.organizations.models import Organization
        return Organization.objects.filter(is_active=True)
    from apps.organizations.models import Organization
    return Organization.objects.filter(
        memberships__user=user,
        memberships__is_active=True,
    ).distinct()
