"""Regression test for ``organizations/0004_backfill_demo_organization``.

The migration exists to heal production envs that were seeded before
PR-13 added the demo ``Organization`` row — those envs have demo
Building/Entrance/Unit rows sitting with ``organization=NULL``, which
breaks the ``/passes/my/`` filter (see commit 5dcf957). The tests below
call the migration's ``backfill_demo_org`` function directly against the
live model registry (``django.apps.apps``), which is the same object the
``apps.get_model`` indirection yields at migration-replay time.

We don't use ``django-test-migrations`` because the repo already vendors
a similar direct-call pattern for the other data migrations (see the
``seed_demo`` test suite) and the extra dependency isn't worth it for a
handful of assertions.
"""
from __future__ import annotations

import pytest
from django.apps import apps as django_apps

from apps.apartments.models import Building, BuildingType, Entrance, Unit
from apps.organizations.models import Organization


# The migration file name begins with a digit, so we load the module by
# path and grab the callable rather than via ``from ... import``. Keep
# this lookup in module scope so test collection fails loud if the
# migration ever gets renamed.
def _load_backfill_callable():
    import importlib.util
    from pathlib import Path

    mig_path = (
        Path(__file__).resolve().parent.parent
        / "organizations"
        / "migrations"
        / "0004_backfill_demo_organization.py"
    )
    spec = importlib.util.spec_from_file_location(
        "apps.organizations.migrations.m0004", mig_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.backfill_demo_org, module.DEMO_ORGANIZATION_NAME


backfill_demo_org, DEMO_ORGANIZATION_NAME = _load_backfill_callable()


@pytest.mark.django_db
class TestBackfillDemoOrganization:
    def test_creates_organization_when_missing(self):
        """On a pristine DB the migration MUST create the demo Org.

        This is the "first deploy on a pre-PR-13 env" case — the whole
        reason the migration exists. We assert the returned row has the
        canonical name and ``is_demo=True`` so the nightly reset can
        still find it.
        """
        # Some conftest fixtures may have pre-populated an Organization
        # row as part of their bootstrap; scrub anything under the demo
        # name so we're genuinely testing the "zero orgs" branch.
        Organization.objects.filter(name=DEMO_ORGANIZATION_NAME).delete()
        assert not Organization.objects.filter(name=DEMO_ORGANIZATION_NAME).exists()

        backfill_demo_org(django_apps, schema_editor=None)

        org = Organization.objects.get(name=DEMO_ORGANIZATION_NAME)
        assert org.is_demo is True
        assert org.is_active is True

    def test_is_idempotent(self):
        """Rerunning the migration must not create a duplicate Org row.

        Django's migration framework will only run a RunPython op once
        per deploy, but we rerun in tests, in CI, and operators sometimes
        squash migrations manually. The ``get_or_create`` key is ``name``
        so two calls MUST converge on the same single row.
        """
        backfill_demo_org(django_apps, schema_editor=None)
        backfill_demo_org(django_apps, schema_editor=None)

        assert (
            Organization.objects.filter(name=DEMO_ORGANIZATION_NAME).count() == 1
        )

    def test_links_demo_building_and_cascades_to_children(self):
        """The production symptom: a demo Building with org=NULL that
        owns Entrance/Unit rows also with org=NULL. After the migration
        all three levels must point at the freshly-ensured Org.

        This is the end-to-end health check that downstream consumers
        (``VehiclePass.save`` walking Unit → Entrance → Building) rely on.
        """
        # Simulate a pre-PR-13 seeded env: demo Building exists but no
        # Org, so all three location levels carry NULL.
        building = Building.objects.create(
            name="Зелений Квартал — Демо",
            address="вул. Академіка Заболотного, 15",
            city="Київ",
            type=BuildingType.APARTMENT_BUILDING,
            is_active=True,
            is_demo=True,
        )
        entrance = Entrance.objects.create(building=building, name="А")
        unit = Unit.objects.create(entrance=entrance, number="105", floor=1)
        # Clear auto-derived FKs — Building.save() doesn't auto-populate
        # org from anywhere (it IS the root), but Entrance/Unit.save()
        # copy from their parent. For the pre-PR-13 simulation we want
        # all three NULL, so strip them explicitly.
        Building.objects.filter(pk=building.pk).update(organization=None)
        Entrance.objects.filter(pk=entrance.pk).update(organization=None)
        Unit.objects.filter(pk=unit.pk).update(organization=None)

        backfill_demo_org(django_apps, schema_editor=None)

        org = Organization.objects.get(name=DEMO_ORGANIZATION_NAME)
        building.refresh_from_db()
        entrance.refresh_from_db()
        unit.refresh_from_db()
        assert building.organization_id == org.pkid
        assert entrance.organization_id == org.pkid
        assert unit.organization_id == org.pkid

    def test_does_not_touch_non_demo_buildings(self):
        """A real customer Building (name NOT matching the demo prefix)
        must be left alone even if it happens to sit with org=NULL.

        The migration keys on ``name__startswith`` the demo prefix plus
        ``organization__isnull`` — a stray customer row without an org
        should stay that way and be assigned an org through the normal
        admin/onboarding flow, not retro-linked to the demo one.
        """
        customer_building = Building.objects.create(
            name="ЖК Лісовий Дворик",
            address="вул. Лісова, 1",
            city="Київ",
            type=BuildingType.APARTMENT_BUILDING,
            is_active=True,
            is_demo=False,
        )

        backfill_demo_org(django_apps, schema_editor=None)

        customer_building.refresh_from_db()
        assert customer_building.organization_id is None

    def test_preserves_existing_building_organization(self):
        """If a demo Building already has ``organization`` set (e.g. the
        nightly reset + reseed landed between our migration being
        authored and this customer deploying), the backfill must not
        overwrite it. ``.update()`` is scoped to ``organization__isnull``
        so this is already the behaviour — this test pins it.
        """
        pre_existing_org = Organization.objects.create(
            name="Some Existing Org",
            type="single_building",
            is_active=True,
        )
        building = Building.objects.create(
            name="Зелений Квартал — Демо · Котедж",
            address="вул. Академіка Заболотного, 17",
            city="Київ",
            type=BuildingType.COTTAGE,
            is_active=True,
            is_demo=True,
            organization=pre_existing_org,
        )

        backfill_demo_org(django_apps, schema_editor=None)

        building.refresh_from_db()
        assert building.organization_id == pre_existing_org.pkid, (
            "migration must not overwrite an existing org FK"
        )
