"""Tests for the ``audit_legacy_apartments`` management command.

The command is a read-only data-health probe used by the
``refactor/remove-legacy-apartment`` migration series.  It must:

* never write to the DB (idempotent, safe to run on prod),
* report accurate counts of bridge/cutover/backfill gaps,
* raise every blocker it was asked to detect,
* exit non-zero under ``--strict`` only when blockers are present,
* produce stable JSON suitable for CI diffing.

Happy-path, blocker-path, and strict-exit-code paths are covered below.
Fixtures build minimal data by hand so the tests don't depend on
``seed_demo`` (which is heavier and has its own dedicated suite).
"""
from __future__ import annotations

import json
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.apartments.models import (
    Apartment,
    Building,
    Entrance,
    ResidentialComplex,
    Unit,
)
from apps.issues.models import Issue
from apps.organizations.models import Organization
from apps.profiles.models import Profile

User = get_user_model()


# ───────────────────────── fixtures ────────────────────────────────────────


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme Homes", slug="acme")


@pytest.fixture
def bridged_factory(db, org):
    """Return a callable that builds a fully-bridged Apartment ↔ Unit pair."""

    def _make(number: str = "1", building_name: str = "Block A"):
        building = Building.objects.create(
            name=building_name, address=f"{building_name} addr", organization=org
        )
        entrance = Entrance.objects.create(building=building, name="1")
        legacy = Apartment.objects.create(
            unit_number=number, building=building_name, floor=1
        )
        unit = Unit.objects.create(
            entrance=entrance,
            number=number,
            floor=1,
            apartment=legacy,
        )
        return legacy, unit, building

    return _make


@pytest.fixture
def tenant_user(db):
    return User.objects.create_user(
        email="tenant@example.com",
        username="tenant",
        first_name="T",
        last_name="U",
        password="x",  # noqa: S106
    )


def _run(capture: str = "stdout", **kwargs):
    """Invoke the command and capture its output."""
    out = StringIO()
    err = StringIO()
    try:
        call_command("audit_legacy_apartments", stdout=out, stderr=err, **kwargs)
        exit_code = 0
    except SystemExit as e:
        exit_code = int(e.code) if e.code is not None else 0
    return out.getvalue(), err.getvalue(), exit_code


# ───────────────────────── happy path ──────────────────────────────────────


class TestAuditEmpty:
    """On an empty DB, the audit should report zero-everything and no blockers."""

    def test_empty_db_has_no_blockers(self, db):
        stdout, _, code = _run(as_json=True)
        payload = json.loads(stdout)
        assert payload["apartment_total"] == 0
        assert payload["issue_total"] == 0
        assert payload["profile_total"] == 0
        assert payload["blockers"] == []
        assert code == 0

    def test_empty_db_strict_exits_zero(self, db):
        _, _, code = _run(as_json=True, strict=True)
        assert code == 0

    def test_text_output_contains_success_line(self, db):
        stdout, _, _ = _run()
        assert "No blockers" in stdout


class TestAuditAllBridged:
    """Fully-bridged data should produce zero blockers."""

    def test_bridged_apartment_no_blockers(self, db, bridged_factory):
        bridged_factory()
        stdout, _, code = _run(as_json=True)
        payload = json.loads(stdout)

        assert payload["apartment_total"] == 1
        assert payload["apartment_without_unit_bridge"] == 0
        assert payload["blockers"] == []
        assert code == 0


# ───────────────────────── blocker paths ───────────────────────────────────


class TestAuditBridgeGap:
    """An Apartment with no Unit reverse link is a blocker for PR-1."""

    def test_unbridged_apartment_is_flagged(self, db):
        Apartment.objects.create(unit_number="13", building="Block B", floor=2)
        stdout, _, code = _run(as_json=True)
        payload = json.loads(stdout)

        assert payload["apartment_total"] == 1
        assert payload["apartment_without_unit_bridge"] == 1
        assert any("not bridged to Unit" in b for b in payload["blockers"])
        assert code == 0  # not strict

    def test_strict_unbridged_exits_one(self, db):
        Apartment.objects.create(unit_number="13", building="Block B", floor=2)
        _, _, code = _run(as_json=True, strict=True)
        assert code == 1


class TestAuditIssueCutover:
    """Issue.apartment set without Issue.unit is a PR-2 blocker.

    After PR-2, ``Issue.save()`` mirrors ``apartment.unit → self.unit``
    whenever a bridge exists; the only way to land in this state now is
    via an *unbridged* Apartment — exactly the shape this audit flags.
    """

    def test_issue_with_apartment_without_unit(self, db, tenant_user):
        legacy = Apartment.objects.create(
            unit_number="orphan", building="Nowhere", floor=1
        )
        Issue.objects.create(
            reported_by=tenant_user,
            title="Leak",
            description="Kitchen tap leaks",
            apartment=legacy,
        )
        stdout, _, _ = _run(as_json=True)
        payload = json.loads(stdout)

        assert payload["issue_with_apartment"] == 1
        assert payload["issue_with_apartment_without_unit"] == 1
        assert any("Issue" in b and "unit" in b for b in payload["blockers"])

    def test_issue_with_both_links_is_clean(
        self, db, bridged_factory, tenant_user
    ):
        legacy, unit, _bld = bridged_factory()
        Issue.objects.create(
            reported_by=tenant_user,
            title="Leak",
            description="Kitchen tap leaks",
            apartment=legacy,
            unit=unit,
        )
        stdout, _, _ = _run(as_json=True)
        payload = json.loads(stdout)

        assert payload["issue_with_apartment"] == 1
        assert payload["issue_with_apartment_without_unit"] == 0


class TestAuditProfileUnitGap:
    """A user with legacy Apartment.tenant but no Profile.unit is a PR-3 blocker."""

    def test_user_without_profile_unit(self, db, bridged_factory, tenant_user):
        legacy, unit, _bld = bridged_factory()
        legacy.tenant = tenant_user
        legacy.save()
        # Profile is created via signal on user creation; leave profile.unit None.

        stdout, _, _ = _run(as_json=True)
        payload = json.loads(stdout)

        assert payload["users_with_legacy_apartment"] == 1
        assert payload["users_with_legacy_apartment_missing_profile_unit"] == 1
        assert any("profile.unit" in b for b in payload["blockers"])

    def test_user_with_profile_unit_is_clean(
        self, db, bridged_factory, tenant_user
    ):
        legacy, unit, _bld = bridged_factory()
        legacy.tenant = tenant_user
        legacy.save()
        profile, _ = Profile.objects.get_or_create(user=tenant_user)
        profile.unit = unit
        profile.save()

        stdout, _, _ = _run(as_json=True)
        payload = json.loads(stdout)

        assert payload["users_with_legacy_apartment_missing_profile_unit"] == 0


class TestAuditBuildingStringNormalisation:
    """Whitespace/case variants in Apartment.building must be surfaced."""

    def test_near_duplicate_building_strings(self, db):
        Apartment.objects.create(unit_number="1", building="Block A", floor=1)
        Apartment.objects.create(unit_number="2", building=" Block A", floor=1)
        Apartment.objects.create(unit_number="3", building="block a", floor=1)

        stdout, _, _ = _run(as_json=True)
        payload = json.loads(stdout)

        assert payload["distinct_building_strings"] == 3
        # All three normalise to "block a", making one duplicate group.
        assert len(payload["duplicate_building_strings"]) == 1
        assert payload["duplicate_building_strings"][0][0] == "block a"

    def test_whitespace_variants_listed(self, db):
        Apartment.objects.create(
            unit_number="1", building=" Block A", floor=1
        )
        stdout, _, _ = _run(as_json=True)
        payload = json.loads(stdout)

        assert " Block A" in payload["building_strings_with_whitespace"]


class TestAuditBuildingOrgFk:
    """Buildings without organization FK are a multi-tenant isolation hole."""

    def test_building_without_org_is_blocker(self, db):
        Building.objects.create(name="Orphan", address="—", organization=None)
        stdout, _, code = _run(as_json=True)
        payload = json.loads(stdout)

        assert payload["buildings_without_organization"] == 1
        assert any("NO organization FK" in b for b in payload["blockers"])


class TestAuditComplexOrgMapping:
    """A ResidentialComplex whose buildings span >1 org is ambiguous for PR-8."""

    def test_ambiguous_complex_is_listed(self, db):
        org_a = Organization.objects.create(name="A", slug="a")
        org_b = Organization.objects.create(name="B", slug="b")
        complex_ = ResidentialComplex.objects.create(name="Ambiguous ЖК")
        Building.objects.create(
            name="B1", address="x", organization=org_a, complex=complex_
        )
        Building.objects.create(
            name="B2", address="y", organization=org_b, complex=complex_
        )

        stdout, _, _ = _run(as_json=True)
        payload = json.loads(stdout)

        assert "Ambiguous ЖК" in payload["complex_to_org_ambiguous"]
        assert any("span multiple" in b for b in payload["blockers"])


# ───────────────────────── idempotence / read-only ─────────────────────────


class TestAuditIsReadOnly:
    """The audit must never mutate the DB, regardless of arguments."""

    def test_run_twice_same_counts(self, db, bridged_factory, tenant_user):
        legacy, unit, _bld = bridged_factory()
        legacy.tenant = tenant_user
        legacy.save()

        first, _, _ = _run(as_json=True)
        second, _, _ = _run(as_json=True)
        assert json.loads(first) == json.loads(second)

    def test_run_does_not_create_rows(self, db, bridged_factory, tenant_user):
        legacy, _unit, _bld = bridged_factory()
        legacy.tenant = tenant_user
        legacy.save()

        before = {
            "apt": Apartment.objects.count(),
            "unit": Unit.objects.count(),
            "bld": Building.objects.count(),
            "entr": Entrance.objects.count(),
            "issue": Issue.objects.count(),
            "user": User.objects.count(),
        }
        _run(as_json=True)
        _run(as_json=True, strict=True)
        after = {
            "apt": Apartment.objects.count(),
            "unit": Unit.objects.count(),
            "bld": Building.objects.count(),
            "entr": Entrance.objects.count(),
            "issue": Issue.objects.count(),
            "user": User.objects.count(),
        }
        assert before == after
