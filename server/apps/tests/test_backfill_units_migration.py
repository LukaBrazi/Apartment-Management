"""Tests for the ``0004_backfill_units_from_legacy_apartments`` data migration.

Covers the four backfill branches:

1. Synthesise Building/Entrance/Unit for every unbridged Apartment.
2. Backfill Issue.unit where only apartment was set.
3. Backfill Profile.unit where only Apartment.tenant was set.
4. Adopt orphan Building into the sole Organization when unambiguous;
   leave alone when more than one Organization exists.

We also verify the migration is **idempotent** — running its forward
function twice on the same data must not create duplicate rows or change
counts beyond the first pass.  The audit command is invoked at the end
of the happy-path test to prove "zero blockers" is reachable via this
migration without any application-code changes.
"""
from __future__ import annotations

import importlib
import json
from io import StringIO

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.core.management import call_command

# Django migration module names start with a digit, so a plain ``import``
# statement can't reach them; ``importlib.import_module`` is the
# idiomatic workaround.  We pass the live app registry when calling the
# function, which mirrors what Django does during a forward ``migrate``.
_MIGRATION = importlib.import_module(
    "apps.apartments.migrations.0004_backfill_units_from_legacy_apartments"
)
backfill_units = _MIGRATION.backfill_units

from apps.apartments.models import (  # noqa: E402
    Apartment,
    Building,
    Entrance,
    Unit,
)
from apps.issues.models import Issue  # noqa: E402
from apps.organizations.models import Organization  # noqa: E402
from apps.profiles.models import Profile  # noqa: E402

User = get_user_model()


# ── helpers ────────────────────────────────────────────────────────────────


def _run_migration():
    backfill_units(django_apps, schema_editor=None)


def _audit_payload() -> dict:
    out = StringIO()
    call_command("audit_legacy_apartments", stdout=out, as_json=True)
    return json.loads(out.getvalue())


# ── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme Homes", slug="acme")


@pytest.fixture
def tenant(db):
    return User.objects.create_user(
        email="t@example.com",
        username="t",
        first_name="T",
        last_name="U",
        password="x",  # noqa: S106
    )


# ── tests ──────────────────────────────────────────────────────────────────


class TestBackfillSynthesisesUnit:
    """Unbridged legacy Apartment → synthetic Building/Entrance/Unit."""

    def test_creates_building_entrance_unit(self, db):
        Apartment.objects.create(unit_number="12", building="Block A", floor=3)

        _run_migration()

        apt = Apartment.objects.get(unit_number="12")
        assert apt.unit is not None, "Apartment.unit reverse OneToOne must resolve"
        assert apt.unit.number == "12"
        assert apt.unit.floor == 3
        assert apt.unit.entrance.name == "1"
        assert apt.unit.entrance.building.name == "Block A"

    def test_normalises_building_string(self, db):
        """Leading/trailing whitespace collapses to a single Building row."""
        Apartment.objects.create(unit_number="1", building=" Block A ", floor=1)
        Apartment.objects.create(unit_number="2", building="Block A", floor=1)

        _run_migration()

        assert Building.objects.filter(name="Block A").count() == 1
        assert Unit.objects.count() == 2

    def test_blank_building_becomes_unknown(self, db):
        Apartment.objects.create(unit_number="13", building="", floor=2)

        _run_migration()

        assert Building.objects.filter(name="Unknown").exists()
        assert Unit.objects.filter(number="13").exists()

    def test_is_idempotent(self, db):
        Apartment.objects.create(unit_number="99", building="Block Z", floor=5)

        _run_migration()
        counts_after_first = (
            Building.objects.count(),
            Entrance.objects.count(),
            Unit.objects.count(),
        )

        _run_migration()
        counts_after_second = (
            Building.objects.count(),
            Entrance.objects.count(),
            Unit.objects.count(),
        )

        assert counts_after_first == counts_after_second


class TestBackfillIssueUnit:
    """Issue with apartment FK but no unit FK → unit populated post-migration."""

    def test_issue_unit_is_filled(self, db, tenant):
        apt = Apartment.objects.create(
            unit_number="5", building="Block B", floor=1
        )
        issue = Issue.objects.create(
            reported_by=tenant,
            title="Leak",
            description="kitchen tap",
            apartment=apt,
        )
        assert issue.unit_id is None

        _run_migration()
        issue.refresh_from_db()
        apt.refresh_from_db()

        assert apt.unit is not None
        assert issue.unit_id == apt.unit.pkid


class TestBackfillProfileUnit:
    """User with Apartment.tenant + empty Profile.unit → Profile.unit filled."""

    def test_profile_unit_is_filled(self, db, tenant):
        apt = Apartment.objects.create(
            unit_number="7", building="Block C", floor=2, tenant=tenant
        )
        # Profile is created by post_save signal on User; confirm it's empty.
        profile = Profile.objects.get(user=tenant)
        assert profile.unit_id is None

        _run_migration()

        profile.refresh_from_db()
        apt.refresh_from_db()
        assert apt.unit is not None
        assert profile.unit_id == apt.unit.pkid

    def test_does_not_overwrite_existing_profile_unit(self, db, tenant):
        """Operator edits on Profile.unit must win over backfill."""
        # Pre-existing unit unrelated to the legacy apartment.
        building = Building.objects.create(name="Block X", address="x")
        entrance = Entrance.objects.create(building=building, name="1")
        existing_unit = Unit.objects.create(
            entrance=entrance, number="999", floor=1
        )
        profile = Profile.objects.get(user=tenant)
        profile.unit = existing_unit
        profile.save()

        Apartment.objects.create(
            unit_number="7", building="Block C", floor=2, tenant=tenant
        )

        _run_migration()

        profile.refresh_from_db()
        assert profile.unit_id == existing_unit.pkid


class TestBackfillOrphanBuildingAdoption:
    """Orphan Building + exactly one Organization → Building adopted."""

    def test_single_org_adopts_orphan_buildings(self, db, org):
        Building.objects.create(name="Orphan 1", address="x")
        Building.objects.create(name="Orphan 2", address="y")

        _run_migration()

        for b in Building.objects.all():
            assert b.organization_id == org.pkid, (
                f"Building {b.name} was not adopted into sole Organization"
            )

    def test_multi_org_leaves_orphans_alone(self, db):
        Organization.objects.create(name="A", slug="a")
        Organization.objects.create(name="B", slug="b")
        orphan = Building.objects.create(name="Orphan", address="x")

        _run_migration()

        orphan.refresh_from_db()
        assert orphan.organization_id is None, (
            "Ambiguous org → migration must NOT pick one arbitrarily"
        )


class TestAuditClearsAfterMigration:
    """End-to-end: seed realistic legacy gaps → run migration → audit = clean."""

    def test_audit_reports_no_blockers_after_migration(self, db, org, tenant):
        # A legacy Apartment + Issue + user link, plus an orphan Building.
        apt = Apartment.objects.create(
            unit_number="12", building="Block A", floor=3, tenant=tenant
        )
        Issue.objects.create(
            reported_by=tenant,
            title="Leak",
            description="kitchen tap",
            apartment=apt,
        )

        before = _audit_payload()
        # Baseline confirms the fixture produces real blockers (test is real).
        assert before["blockers"], "setup must yield at least one blocker"

        _run_migration()

        after = _audit_payload()
        assert after["blockers"] == [], (
            f"Migration did not clear all blockers: {after['blockers']}"
        )
