"""Spільні permission classes для всього проєкту.

Замінюють silent-except паттерн в passes/permissions.py та issues/views.py.

Ключові інваріанти:

* Жодного ``except Exception: pass``. Тільки ``Profile.DoesNotExist`` ловиться
  явно — і логується ``logger.warning`` для видимості race-condition'ів
  (юзер створений, але сигнал-бекап профілю ще не виконався).
* ``IsStaff`` приймає три кейси: ``is_superuser``, ``is_staff`` (django-flag —
  у цьому проєкті це і є "dispatcher"), та ``profile.occupation == "guard"``
  (зберегли legacy-доступ guard'а до admin-only ендпоінтів — read-only
  для awareness; див. issues/views.py:IssueListAPIView).
* ``IsStaffOrSuperUser`` — backward-compat alias на ``IsStaff``, щоб не
  ламати існуючі імпорти в issues/views.py.
"""

from __future__ import annotations

import logging
from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.profiles.models import Profile

logger = logging.getLogger(__name__)


def _user_occupation(user) -> str | None:
    """Return user.profile.occupation, or None if profile is missing.

    Logs a warning if Profile.DoesNotExist — that means the post-save
    signal that auto-creates Profile failed, or the row was deleted
    out-of-band. We never silently swallow other exceptions.
    """
    try:
        return user.profile.occupation
    except Profile.DoesNotExist:
        logger.warning(
            "Permission check failed: user %s has no profile", user.pk
        )
        return None


class _OccupationPermission(BasePermission):
    """Base for permissions that gate on Profile.occupation."""

    occupations: tuple[str, ...] = ()

    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        occupation = _user_occupation(user)
        if occupation is None:
            return False
        return occupation in self.occupations


class IsGuard(_OccupationPermission):
    """User whose ``profile.occupation == "guard"``."""

    occupations = ("guard",)


class IsTenant(_OccupationPermission):
    """User whose ``profile.occupation == "tenant"``."""

    occupations = ("tenant",)


class IsStaff(BasePermission):
    """Superuser, ``is_staff`` flag, or guard occupation.

    The guard branch preserves the legacy behaviour of
    ``apps.issues.views.IsStaffOrSuperUser`` — guards retain read access
    to admin-only issue endpoints for awareness.
    """

    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        return _user_occupation(user) == "guard"


class IsGuardOrAdmin(BasePermission):
    """Composite — guard occupation OR superuser/is_staff."""

    def has_permission(self, request: Request, view: Any) -> bool:
        return IsGuard().has_permission(request, view) or IsStaff().has_permission(
            request, view
        )


# Backward-compat alias for existing imports (apps.issues.views).
IsStaffOrSuperUser = IsStaff
