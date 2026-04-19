"""Tests for the Issue dual-read guarantee introduced in PR-2.

During the ``refactor/remove-legacy-apartment`` series, legacy callers
may still write ``Issue.apartment`` while new code already reads
``Issue.unit``.  ``Issue.save()`` bridges the two by mirroring
``apartment.unit → self.unit`` whenever the explicit ``unit`` is None.

These tests lock in that contract so PR-3 serializers and PR-4 frontend
can rely on ``Issue.unit`` being populated regardless of how the row was
written.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.apartments.models import Apartment, Building, Entrance, Unit
from apps.issues.models import Issue

User = get_user_model()


# ───────────────────────── fixtures ────────────────────────────────────────


@pytest.fixture
def tenant(db):
    return User.objects.create_user(
        email="tenant@example.com",
        username="tenant",
        first_name="T",
        last_name="U",
        password="x",  # noqa: S106
    )


@pytest.fixture
def bridged(db):
    """Return (apartment, unit) linked via Unit.apartment OneToOne."""
    apt = Apartment.objects.create(unit_number="5", building="Block A", floor=1)
    building = Building.objects.create(name="Block A", address="Block A")
    entrance = Entrance.objects.create(building=building, name="1")
    unit = Unit.objects.create(
        entrance=entrance, number="5", floor=1, apartment=apt
    )
    return apt, unit


# ───────────────────────── tests ───────────────────────────────────────────


class TestIssueSaveAutoSyncUnit:
    """Writing apartment alone must still populate unit on save."""

    def test_legacy_write_fills_unit(self, db, tenant, bridged):
        apt, unit = bridged

        issue = Issue.objects.create(
            reported_by=tenant,
            title="Leak",
            description="kitchen",
            apartment=apt,
            # unit NOT passed — mimics legacy writer
        )

        assert issue.unit_id == unit.pkid, (
            "Issue.save() must mirror apartment.unit → self.unit"
        )

    def test_explicit_unit_is_preserved(self, db, tenant, bridged):
        """Operator-set unit must never be overwritten by the apartment link."""
        apt, _unit = bridged
        # Independent unit not associated with the legacy apartment.
        other_building = Building.objects.create(name="Block Z", address="z")
        other_entrance = Entrance.objects.create(building=other_building, name="1")
        other_unit = Unit.objects.create(
            entrance=other_entrance, number="777", floor=7
        )

        issue = Issue.objects.create(
            reported_by=tenant,
            title="Electrical",
            description="panel",
            apartment=apt,
            unit=other_unit,  # explicit — must win
        )

        assert issue.unit_id == other_unit.pkid

    def test_no_apartment_no_unit_stays_none(self, db, tenant):
        """An Issue with neither link must not fabricate a unit."""
        issue = Issue.objects.create(
            reported_by=tenant,
            title="Generic",
            description="no location",
        )
        assert issue.unit_id is None
        assert issue.apartment_id is None

    def test_apartment_without_unit_stays_none(self, db, tenant):
        """A legacy Apartment with no bridged Unit can't magically grow one."""
        apt = Apartment.objects.create(
            unit_number="orphan", building="Nowhere", floor=1
        )
        issue = Issue.objects.create(
            reported_by=tenant,
            title="No unit",
            description="orphan apartment",
            apartment=apt,
        )
        assert issue.unit_id is None

    def test_resave_does_not_overwrite_unit_cleared_intentionally(
        self, db, tenant, bridged
    ):
        """If an admin clears Issue.unit (edge case), save() restores it."""
        apt, unit = bridged
        issue = Issue.objects.create(
            reported_by=tenant,
            title="Leak",
            description="kitchen",
            apartment=apt,
        )
        assert issue.unit_id == unit.pkid

        # Force-clear unit and re-save with update_fields ─ save should
        # restore it (the rule is "apartment-derived unit wins over null").
        issue.unit = None
        issue.save(update_fields=["unit"])
        issue.refresh_from_db()
        assert issue.unit_id == unit.pkid

    def test_update_fields_is_extended_to_include_unit(
        self, db, tenant, bridged
    ):
        """save(update_fields=[...]) must still persist the synced unit."""
        apt, unit = bridged
        # Create without unit, then set apartment later via update_fields.
        other_apt = Apartment.objects.create(
            unit_number="999", building="Nowhere", floor=9
        )
        issue = Issue.objects.create(
            reported_by=tenant,
            title="Will relocate",
            description="x",
            apartment=other_apt,  # no bridged Unit for this one
        )
        assert issue.unit_id is None

        # Now point at the bridged apartment via update_fields
        issue.apartment = apt
        issue.unit = None
        issue.save(update_fields=["apartment", "unit"])

        issue.refresh_from_db()
        assert issue.unit_id == unit.pkid
