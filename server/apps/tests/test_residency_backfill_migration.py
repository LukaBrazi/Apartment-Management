"""PR-10: verify the data migration produces Residency rows matching
existing ``Profile.unit`` FKs.

Running the migration end-to-end via ``django-migrate`` is awkward in
pytest-django (the test DB is already fully migrated by the fixture
setup), so we instead invoke the migration's ``backfill`` function
directly against the live DB state, then assert invariants.  The
function is written to be idempotent so running it on a freshly-seeded
DB is safe.
"""
from __future__ import annotations

from importlib import import_module

import pytest
from django.apps import apps as django_apps

from apps.apartments.models import Residency, ResidencyRole
from apps.profiles.models import Profile
from apps.tests.factories import UnitFactory, UserFactory

pytestmark = pytest.mark.django_db

# The migration lives in apartments/migrations.  We load it by module
# path so we don't couple to a specific filename drift.
MIGRATION_MODULE = (
    "apps.apartments.migrations.0009_backfill_residency_from_profile"
)


def _run_backfill():
    mod = import_module(MIGRATION_MODULE)
    mod.backfill(django_apps, schema_editor=None)


def test_backfill_creates_one_primary_residency_per_profile():
    user = UserFactory()
    unit = UnitFactory()
    profile = Profile.objects.get(user=user)
    profile._skip_residency_mirror = True
    profile.unit = unit
    profile.save()

    # Sanity: mirror was skipped.
    assert Residency.objects.filter(user=user).count() == 0

    _run_backfill()

    residencies = Residency.objects.filter(user=user)
    assert residencies.count() == 1
    row = residencies.first()
    assert row.unit_id == unit.pk
    assert row.is_primary is True
    assert row.role == ResidencyRole.OWNER


def test_backfill_is_idempotent():
    user = UserFactory()
    unit = UnitFactory()
    profile = Profile.objects.get(user=user)
    profile._skip_residency_mirror = True
    profile.unit = unit
    profile.save()

    _run_backfill()
    _run_backfill()  # second run — must not duplicate

    assert Residency.objects.filter(user=user).count() == 1


def test_backfill_respects_existing_residency():
    """If a Residency already exists for (user, unit), the backfill
    must not duplicate it.  If it is not primary and there's no other
    primary for this user, it is promoted."""
    user = UserFactory()
    unit = UnitFactory()

    # Pre-existing Residency, non-primary.
    Residency.objects.create(
        user=user, unit=unit, role=ResidencyRole.TENANT, is_primary=False
    )

    profile = Profile.objects.get(user=user)
    profile._skip_residency_mirror = True
    profile.unit = unit
    profile.save()

    _run_backfill()

    residencies = Residency.objects.filter(user=user)
    assert residencies.count() == 1
    row = residencies.first()
    assert row.role == ResidencyRole.TENANT  # unchanged
    assert row.is_primary is True  # promoted, since no other primary existed


def test_backfill_skips_profiles_with_no_unit():
    user = UserFactory()
    # Profile has no unit.
    _run_backfill()
    assert Residency.objects.filter(user=user).count() == 0
