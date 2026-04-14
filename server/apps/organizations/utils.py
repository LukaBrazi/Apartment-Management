"""
Утиліти для автоматичного витягування організації користувача.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError


def get_user_primary_organization(user):
    """
    Повертає першу активну організацію користувача.
    Returns None якщо користувач не є членом жодної організації (backward compat).
    """
    if user.is_superuser:
        return None  # superuser не прив'язаний до org

    membership = user.organization_memberships.filter(is_active=True).select_related("organization").first()
    return membership.organization if membership else None  # None instead of raising


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
