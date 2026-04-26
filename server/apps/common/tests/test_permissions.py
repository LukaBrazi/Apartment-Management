"""Tests for shared permission classes in apps.common.permissions.

PR-1 (fix/critical-security) replaces the silent `except Exception: pass`
pattern in passes/permissions.py and issues/views.py with explicit
`Profile.DoesNotExist` handling and a logged warning.
"""
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory

from apps.common.permissions import (
    IsGuard,
    IsGuardOrAdmin,
    IsStaff,
    IsStaffOrSuperUser,
    IsTenant,
)
from apps.profiles.models import Profile

User = get_user_model()


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def factory():
    return APIRequestFactory()


@pytest.fixture
def anon_request(factory):
    request = factory.get("/")
    request.user = AnonymousUser()
    return request


def _set_occupation(user, occupation: str):
    profile = user.profile
    profile.occupation = occupation
    profile.save()
    return user


@pytest.fixture
def guard_user(db):
    user = User.objects.create_user(
        username="perm_guard",
        email="perm_guard@test.com",
        password="Test1234!",
    )
    return _set_occupation(user, Profile.Occupation.GUARD)


@pytest.fixture
def tenant_user(db):
    user = User.objects.create_user(
        username="perm_tenant",
        email="perm_tenant@test.com",
        password="Test1234!",
    )
    return _set_occupation(user, Profile.Occupation.TENANT)


@pytest.fixture
def staff_user(db):
    user = User.objects.create_user(
        username="perm_staff",
        email="perm_staff@test.com",
        password="Test1234!",
        is_staff=True,
    )
    return _set_occupation(user, Profile.Occupation.PLUMBER)


@pytest.fixture
def superuser(db):
    user = User.objects.create_superuser(
        username="perm_super",
        email="perm_super@test.com",
        password="Test1234!",
    )
    return user


@pytest.fixture
def resident_user(db):
    """Plain tenant — not staff, not guard."""
    user = User.objects.create_user(
        username="perm_resident",
        email="perm_resident@test.com",
        password="Test1234!",
    )
    return _set_occupation(user, Profile.Occupation.TENANT)


@pytest.fixture
def user_without_profile(db):
    """User whose Profile row was deleted to simulate the race condition.

    Returns a freshly-fetched ``User`` instance so the OneToOne related
    descriptor isn't holding a cached Profile from before deletion.
    """
    user = User.objects.create_user(
        username="perm_orphan",
        email="perm_orphan@test.com",
        password="Test1234!",
    )
    Profile.objects.filter(user=user).delete()
    return User.objects.get(pk=user.pk)


def _request_for(factory, user):
    request = factory.get("/")
    request.user = user
    return request


# ── IsGuard ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestIsGuard:
    def test_is_guard_returns_true_for_guard_profile(self, factory, guard_user):
        request = _request_for(factory, guard_user)
        assert IsGuard().has_permission(request, MagicMock()) is True

    def test_is_guard_returns_false_for_tenant_profile(self, factory, tenant_user):
        request = _request_for(factory, tenant_user)
        assert IsGuard().has_permission(request, MagicMock()) is False

    def test_is_guard_when_profile_missing_raises_clear_error_or_returns_false_explicitly(
        self, factory, user_without_profile, caplog
    ):
        """Behaviour when Profile is missing must be explicit — no silent except.

        Either raise a clear error or return False with a logged warning.
        Never swallow Exception silently.
        """
        request = _request_for(factory, user_without_profile)
        with caplog.at_level("WARNING", logger="apps.common.permissions"):
            result = IsGuard().has_permission(request, MagicMock())
        assert result is False
        assert any(
            "profile" in r.message.lower() for r in caplog.records
        ), "Expected a warning log mentioning the missing profile"

    def test_is_guard_returns_false_for_anonymous(self, anon_request):
        assert IsGuard().has_permission(anon_request, MagicMock()) is False


# ── IsTenant ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestIsTenant:
    def test_is_tenant_returns_true_for_tenant_profile(self, factory, tenant_user):
        request = _request_for(factory, tenant_user)
        assert IsTenant().has_permission(request, MagicMock()) is True

    def test_is_tenant_returns_false_for_staff_profile(self, factory, staff_user):
        # staff_user occupation is PLUMBER, not TENANT
        request = _request_for(factory, staff_user)
        assert IsTenant().has_permission(request, MagicMock()) is False

    def test_is_tenant_when_profile_missing_returns_false_explicitly(
        self, factory, user_without_profile, caplog
    ):
        request = _request_for(factory, user_without_profile)
        with caplog.at_level("WARNING", logger="apps.common.permissions"):
            result = IsTenant().has_permission(request, MagicMock())
        assert result is False
        assert any("profile" in r.message.lower() for r in caplog.records)

    def test_is_tenant_returns_false_for_anonymous(self, anon_request):
        assert IsTenant().has_permission(anon_request, MagicMock()) is False


# ── IsStaff ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestIsStaff:
    def test_is_staff_returns_true_for_superuser(self, factory, superuser):
        request = _request_for(factory, superuser)
        assert IsStaff().has_permission(request, MagicMock()) is True

    def test_is_staff_returns_true_for_django_is_staff_flag(
        self, factory, staff_user
    ):
        """The convention in this project: dispatcher == User.is_staff=True.

        Profile.Occupation has no 'dispatcher' value; the dispatcher role is
        carried by the Django auth flag ``User.is_staff`` (see
        apps/notifications/utils.py:get_active_dispatcher_chat_ids and
        notifications/tasks.py docstring).  IsStaff() must therefore return
        True for any user with ``is_staff=True`` regardless of occupation.
        """
        request = _request_for(factory, staff_user)
        assert IsStaff().has_permission(request, MagicMock()) is True

    def test_is_staff_returns_true_for_guard_via_occupation(
        self, factory, guard_user
    ):
        """Existing behaviour preserved: guards retain read access to admin
        endpoints that use IsStaffOrSuperUser (see issues/views.py).
        """
        request = _request_for(factory, guard_user)
        assert IsStaff().has_permission(request, MagicMock()) is True

    def test_is_staff_returns_false_for_resident(self, factory, resident_user):
        request = _request_for(factory, resident_user)
        assert IsStaff().has_permission(request, MagicMock()) is False

    def test_is_staff_returns_false_for_anonymous(self, anon_request):
        assert IsStaff().has_permission(anon_request, MagicMock()) is False

    def test_is_staff_when_profile_missing_returns_false_explicitly(
        self, factory, user_without_profile, caplog
    ):
        request = _request_for(factory, user_without_profile)
        with caplog.at_level("WARNING", logger="apps.common.permissions"):
            result = IsStaff().has_permission(request, MagicMock())
        assert result is False
        assert any("profile" in r.message.lower() for r in caplog.records)


# ── IsGuardOrAdmin ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestIsGuardOrAdmin:
    def test_returns_true_for_guard(self, factory, guard_user):
        request = _request_for(factory, guard_user)
        assert IsGuardOrAdmin().has_permission(request, MagicMock()) is True

    def test_returns_true_for_superuser(self, factory, superuser):
        request = _request_for(factory, superuser)
        assert IsGuardOrAdmin().has_permission(request, MagicMock()) is True

    def test_returns_true_for_staff(self, factory, staff_user):
        request = _request_for(factory, staff_user)
        assert IsGuardOrAdmin().has_permission(request, MagicMock()) is True

    def test_returns_false_for_resident(self, factory, resident_user):
        request = _request_for(factory, resident_user)
        assert IsGuardOrAdmin().has_permission(request, MagicMock()) is False

    def test_returns_false_for_anonymous(self, anon_request):
        assert IsGuardOrAdmin().has_permission(anon_request, MagicMock()) is False


# ── Backward-compat alias ───────────────────────────────────────────────────


def test_is_staff_or_super_user_alias_points_to_is_staff():
    """``IsStaffOrSuperUser`` is kept as a backward-compat alias for
    existing imports in apps.issues.views — it must be the same class
    (or a subclass) as ``IsStaff``.
    """
    assert IsStaffOrSuperUser is IsStaff or issubclass(IsStaffOrSuperUser, IsStaff)
