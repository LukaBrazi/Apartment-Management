"""Unit tests for the ``Residency`` through-model (PR-9).

Scope — these tests verify:

* Basic CRUD and defaults (role, is_primary, dates).
* The ``UniqueConstraint(user, unit)`` — a user cannot have two
  residencies on the same unit.
* The partial ``UniqueConstraint(user, is_primary=True)`` — a user may
  have at most one primary residency.  Saving a second primary
  auto-demotes the first via ``Residency.save``.
* ``clean()`` rejects ``end_date < start_date``.
* All declared ``ResidencyRole`` choices accept / round-trip.

The schema-only changes (``Building.type``, ``Building.total_area``,
``Unit.area``, ``Organization.SINGLE_BUILDING``) are covered in
``test_apartment_schema_pr9.py``.
"""
from __future__ import annotations

import datetime as dt

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.apartments.models import Residency, ResidencyRole
from apps.tests.factories import (
    ResidencyFactory,
    UnitFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


# ─── Basic model behavior ─────────────────────────────────────────────────────


def test_residency_created_with_defaults():
    res = ResidencyFactory()
    assert res.pk is not None
    assert res.role == ResidencyRole.OWNER
    assert res.is_primary is False
    assert res.start_date is None
    assert res.end_date is None


def test_residency_str_marks_primary():
    res = ResidencyFactory(is_primary=True)
    assert "★" in str(res)
    res.is_primary = False
    res.save()
    assert "★" not in str(res)


def test_residency_all_role_choices_accepted():
    user = UserFactory()
    for role in ResidencyRole.values:
        unit = UnitFactory()
        res = Residency.objects.create(user=user, unit=unit, role=role)
        assert res.role == role


# ─── Unique (user, unit) ──────────────────────────────────────────────────────


def test_cannot_create_duplicate_user_unit_residency():
    user = UserFactory()
    unit = UnitFactory()
    Residency.objects.create(user=user, unit=unit, role=ResidencyRole.OWNER)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Residency.objects.create(
                user=user, unit=unit, role=ResidencyRole.TENANT
            )


def test_same_user_different_units_allowed():
    """A multi-unit owner case — two residencies for the same user on
    different units must be permitted.  This is the whole point of the
    through-model."""
    user = UserFactory()
    unit_a = UnitFactory()
    unit_b = UnitFactory()
    Residency.objects.create(user=user, unit=unit_a)
    Residency.objects.create(user=user, unit=unit_b)
    assert user.residencies.count() == 2


def test_same_unit_different_users_allowed():
    """Two residents sharing the same unit (e.g. owner + family) must
    be representable."""
    owner = UserFactory()
    family = UserFactory()
    unit = UnitFactory()
    Residency.objects.create(user=owner, unit=unit, role=ResidencyRole.OWNER)
    Residency.objects.create(user=family, unit=unit, role=ResidencyRole.FAMILY)
    assert unit.residencies.count() == 2


# ─── Partial unique: one primary per user ─────────────────────────────────────


def test_first_primary_residency_persists():
    res = ResidencyFactory(is_primary=True)
    res.refresh_from_db()
    assert res.is_primary is True


def test_second_primary_demotes_first_on_save():
    user = UserFactory()
    first = Residency.objects.create(
        user=user, unit=UnitFactory(), is_primary=True
    )
    second = Residency.objects.create(
        user=user, unit=UnitFactory(), is_primary=True
    )

    first.refresh_from_db()
    second.refresh_from_db()

    assert second.is_primary is True
    assert first.is_primary is False  # auto-demoted
    assert (
        Residency.objects.filter(user=user, is_primary=True).count() == 1
    )


def test_promoting_existing_residency_to_primary_demotes_sibling():
    """``res.is_primary = True; res.save()`` (not create) must also
    demote the existing primary — that's the common admin flow."""
    user = UserFactory()
    first = Residency.objects.create(
        user=user, unit=UnitFactory(), is_primary=True
    )
    second = Residency.objects.create(
        user=user, unit=UnitFactory(), is_primary=False
    )

    second.is_primary = True
    second.save()

    first.refresh_from_db()
    assert first.is_primary is False
    assert (
        Residency.objects.filter(user=user, is_primary=True).count() == 1
    )


def test_primary_is_per_user_not_global():
    """Two different users each hold their own primary residency."""
    user_a = UserFactory()
    user_b = UserFactory()
    Residency.objects.create(user=user_a, unit=UnitFactory(), is_primary=True)
    Residency.objects.create(user=user_b, unit=UnitFactory(), is_primary=True)

    assert Residency.objects.filter(is_primary=True).count() == 2


def test_non_primary_residencies_may_coexist():
    """Only *primary* residencies are constrained to at most one per
    user.  Non-primary rows for the same user must coexist freely."""
    user = UserFactory()
    Residency.objects.create(user=user, unit=UnitFactory(), is_primary=False)
    Residency.objects.create(user=user, unit=UnitFactory(), is_primary=False)
    Residency.objects.create(user=user, unit=UnitFactory(), is_primary=False)
    assert Residency.objects.filter(user=user, is_primary=False).count() == 3


# ─── Date validation ─────────────────────────────────────────────────────────


def test_clean_rejects_end_before_start():
    res = ResidencyFactory.build(
        user=UserFactory(),
        unit=UnitFactory(),
        start_date=dt.date(2026, 1, 10),
        end_date=dt.date(2026, 1, 5),
    )
    with pytest.raises(ValidationError) as exc:
        res.clean()
    assert "end_date" in exc.value.message_dict


def test_clean_allows_equal_start_end():
    day = dt.date(2026, 1, 10)
    res = ResidencyFactory.build(
        user=UserFactory(), unit=UnitFactory(),
        start_date=day, end_date=day,
    )
    res.clean()  # no raise


def test_clean_allows_open_ended_dates():
    res = ResidencyFactory.build(
        user=UserFactory(), unit=UnitFactory(),
        start_date=dt.date(2026, 1, 1), end_date=None,
    )
    res.clean()  # no raise

    res2 = ResidencyFactory.build(
        user=UserFactory(), unit=UnitFactory(),
        start_date=None, end_date=dt.date(2026, 1, 1),
    )
    res2.clean()  # no raise


# ─── Cascade behavior ─────────────────────────────────────────────────────────


def test_residency_deleted_when_unit_deleted():
    unit = UnitFactory()
    res = ResidencyFactory(unit=unit)
    pk = res.pk
    unit.delete()
    assert not Residency.objects.filter(pk=pk).exists()


def test_residency_deleted_when_user_deleted():
    user = UserFactory()
    res = ResidencyFactory(user=user)
    pk = res.pk
    user.delete()
    assert not Residency.objects.filter(pk=pk).exists()
