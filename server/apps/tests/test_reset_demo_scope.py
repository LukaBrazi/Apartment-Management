"""BLOCKING safety tests for ``apps.common.seed.reset_scope.reset_demo_scope``.

Per ``docs/DEMO_SEED_PLAN.md`` §11.2: these tests are a deploy gate.  If any
of them regress, ``seed_demo --reset`` MUST NOT run on production.  The risks:

* Deleting a real customer's account (email outside ``@demo.com``).
* Deleting Django superuser (even if its email happens to end with ``@demo.com``).
* Widening scope via env-var override (shouldn't be possible — constants live
  in code, not in settings).

Keep this file focused on *reset* invariants.  Seed-module-specific tests go
into ``test_seed_demo.py``; the orchestrator integration test lives there too.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.apartments.models import Building
from apps.common.seed.helpers import DEMO_BUILDING_NAME, DEMO_EMAIL_DOMAIN
from apps.common.seed.reset_scope import (
    DemoResetSafetyError,
    ResetReport,
    reset_demo_scope,
)

User = get_user_model()


# ──────────────────── fixtures (shared across the file) ──────────────────────


@pytest.fixture
def real_users(db):
    """Three production-like users on a different email domain."""
    a = User.objects.create_user(
        email="manager@customer.example",
        username="manager_customer",
        first_name="Iryna",
        last_name="Petrova",
        password="x",  # noqa: S106
    )
    b = User.objects.create_user(
        email="resident@realbuilding.ua",
        username="resident_realbuilding",
        first_name="Bohdan",
        last_name="Hryhorenko",
        password="x",  # noqa: S106
    )
    c = User.objects.create_user(
        email="staff@otherdomain.org",
        username="staff_otherdomain",
        first_name="Olena",
        last_name="Korniichuk",
        password="x",  # noqa: S106
    )
    return a, b, c


@pytest.fixture
def demo_users(db):
    """Users that ``reset_demo_scope`` is expected to delete."""
    d = User.objects.create_user(
        email="dispatcher@demo.com",
        username="dispatcher_demo",
        first_name="Tetiana",
        last_name="Romanenko",
        password="x",  # noqa: S106
    )
    r = User.objects.create_user(
        email="tenant@demo.com",
        username="tenant_demo",
        first_name="Ivan",
        last_name="Test",
        password="x",  # noqa: S106
    )
    return d, r


@pytest.fixture
def real_building(db):
    return Building.objects.create(
        name="Реальний ЖК на Печерську",
        address="вул. Грушевського, 1",
        city="Київ",
        is_active=True,
    )


@pytest.fixture
def demo_building(db):
    return Building.objects.create(
        name=DEMO_BUILDING_NAME,
        address="вул. Академіка Заболотного, 15",
        city="Київ",
        is_active=True,
    )


# ───────────────────────────── pin / drift tests ─────────────────────────────


def test_demo_email_domain_constant_is_stable():
    """Renaming ``DEMO_EMAIL_DOMAIN`` requires an explicit migration discussion.

    If this test fails, ask yourself: do we really want to widen the reset
    filter?  If yes, update ``reset_scope.py`` and the K8s CronJob docs in
    the same PR.
    """
    assert DEMO_EMAIL_DOMAIN == "@demo.com"


def test_demo_building_name_constant_is_stable():
    """Same rationale as above but for the Building marker.

    Renaming here means an existing demo building row would survive the next
    reset — possibly indefinitely if nobody notices.
    """
    assert DEMO_BUILDING_NAME == "Зелений Квартал — Демо"


# ──────────────────────── core safety invariant test ─────────────────────────


@pytest.mark.django_db
def test_reset_demo_does_not_touch_real_users_or_superuser(
    real_users, demo_users, real_building, demo_building,
):
    """The one test that must never regress.

    Mirrors the worst-case production scenario: a mixed DB with real
    customers, a superuser, and demo data seeded on top.  Reset should
    leave everything except the demo scope alone.
    """
    real_a, real_b, real_c = real_users
    demo_dispatcher, demo_tenant = demo_users

    # Superuser explicitly gets a @demo.com email to test the HARD GUARD:
    # even if DEMO_EMAIL_DOMAIN matches, is_superuser=True must protect it.
    superuser = User.objects.create_superuser(
        email="ops@demo.com",
        username="ops_superuser",
        first_name="Ops",
        last_name="Admin",
        password="x",  # noqa: S106
    )

    report = reset_demo_scope()

    # Returned report shape + values ------------------------------------------------
    assert isinstance(report, ResetReport)
    assert report.dry_run is False
    assert report.demo_users_matched == 2  # dispatcher + tenant, NOT superuser
    assert report.demo_buildings_matched == 1

    # Real data survives --------------------------------------------------------------
    for user in (real_a, real_b, real_c, superuser):
        assert User.objects.filter(pk=user.pk).exists(), (
            f"Real/super user {user.email} was deleted by reset!"
        )
    assert Building.objects.filter(pk=real_building.pk).exists()

    # Demo data is gone ---------------------------------------------------------------
    assert not User.objects.filter(pk=demo_dispatcher.pk).exists()
    assert not User.objects.filter(pk=demo_tenant.pk).exists()
    assert not Building.objects.filter(pk=demo_building.pk).exists()


# ───────────────────── individual boundary-condition tests ───────────────────


@pytest.mark.django_db
def test_superuser_with_demo_email_is_never_deleted():
    """``is_superuser=True`` trumps the email match — this is the HARD GUARD."""
    superuser = User.objects.create_superuser(
        email="admin@demo.com",
        username="admin_demo",
        first_name="Admin",
        last_name="Root",
        password="x",  # noqa: S106
    )
    reset_demo_scope()
    assert User.objects.filter(pk=superuser.pk).exists()


@pytest.mark.django_db
def test_real_building_with_similar_name_is_not_deleted():
    """Filter uses exact ``name==`` match, not ``icontains`` or ``startswith``."""
    decoys = [
        Building.objects.create(name="Зелений Квартал", address="a", city="Київ"),
        Building.objects.create(name="Зелений Квартал 2", address="b", city="Київ"),
        Building.objects.create(
            name=DEMO_BUILDING_NAME + " копія", address="c", city="Київ",
        ),
    ]
    target = Building.objects.create(
        name=DEMO_BUILDING_NAME, address="d", city="Київ",
    )

    report = reset_demo_scope()

    assert report.demo_buildings_matched == 1
    assert not Building.objects.filter(pk=target.pk).exists()
    for decoy in decoys:
        assert Building.objects.filter(pk=decoy.pk).exists(), (
            f"Decoy building {decoy.name!r} was wrongly deleted"
        )


@pytest.mark.django_db
def test_email_match_is_case_insensitive_and_suffix_only():
    """``email__iendswith`` — matches ``@demo.com`` regardless of case.

    Users whose local-part merely *contains* the domain (``demo.com@real.io``)
    are NOT matched.
    """
    target_lower = User.objects.create_user(
        email="lower@demo.com", username="ul", password="x",  # noqa: S106
    )
    target_upper = User.objects.create_user(
        email="UPPER@Demo.Com", username="uu", password="x",  # noqa: S106
    )
    impersonator = User.objects.create_user(
        email="demo.com@real.io", username="imp", password="x",  # noqa: S106
    )

    reset_demo_scope()

    assert not User.objects.filter(pk=target_lower.pk).exists()
    assert not User.objects.filter(pk=target_upper.pk).exists()
    assert User.objects.filter(pk=impersonator.pk).exists()


# ───────────────────────────── dry-run behaviour ─────────────────────────────


@pytest.mark.django_db
def test_dry_run_does_not_delete_anything(demo_users, demo_building):
    report = reset_demo_scope(dry_run=True)

    assert report.dry_run is True
    assert report.demo_users_matched == 2
    assert report.demo_buildings_matched == 1

    # Nothing was touched.
    assert User.objects.filter(email__iendswith=DEMO_EMAIL_DOMAIN).count() == 2
    assert Building.objects.filter(name=DEMO_BUILDING_NAME).exists()


@pytest.mark.django_db
def test_dry_run_on_empty_database_returns_zeroes():
    report = reset_demo_scope(dry_run=True)
    assert report.demo_users_matched == 0
    assert report.demo_buildings_matched == 0


# ───────────────────────────── idempotency test ──────────────────────────────


@pytest.mark.django_db
def test_running_reset_twice_is_idempotent(demo_users, demo_building):
    """Second reset is a no-op — useful for the CronJob retry scenario."""
    first = reset_demo_scope()
    second = reset_demo_scope()

    assert first.demo_users_matched == 2
    assert first.demo_buildings_matched == 1
    assert second.demo_users_matched == 0
    assert second.demo_buildings_matched == 0


# ───────────────────────── counts / report correctness ───────────────────────


@pytest.mark.django_db
def test_report_counts_preserved_users_correctly(real_users, demo_users):
    # 3 real + 2 demo + 0 superusers (yet)
    report = reset_demo_scope()
    # All 3 real users survive (none is superuser, none is demo scope).
    assert report.non_demo_users_preserved == 3
    assert report.superusers_preserved == 0


@pytest.mark.django_db
def test_report_counts_superusers_correctly():
    User.objects.create_superuser(
        email="op1@internal.co", username="op1", password="x",  # noqa: S106
    )
    User.objects.create_superuser(
        email="op2@internal.co", username="op2", password="x",  # noqa: S106
    )
    User.objects.create_user(
        email="demo1@demo.com", username="demo1", password="x",  # noqa: S106
    )
    report = reset_demo_scope()

    assert report.superusers_preserved == 2
    assert report.demo_users_matched == 1


# ───────────────────────────── public surface ────────────────────────────────


def test_public_api_surface():
    """Guard against accidentally removing exported symbols.

    The orchestrator imports these names — renaming them without updating
    the orchestrator will hard-fail the seed command on prod.
    """
    from apps.common.seed import reset_scope

    assert hasattr(reset_scope, "reset_demo_scope")
    assert hasattr(reset_scope, "ResetReport")
    assert hasattr(reset_scope, "DemoResetSafetyError")
    # Exception hierarchy — callers may write generic error handlers.
    assert issubclass(DemoResetSafetyError, RuntimeError)
