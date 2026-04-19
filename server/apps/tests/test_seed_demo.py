"""Integration tests for ``seed_demo`` orchestrator (plan §14).

Covers the full pipeline — building → users → issues → posts → passes →
ratings — plus CLI safety paths (``--dry-run`` without ``--reset``,
``--passwords-from-env`` without ``DEMO_PASSWORD``).

Per-module unit tests live next to each seed module; these tests guard
the *orchestrator contract* — that running the command end-to-end
produces the exact aggregates the demo UX relies on.

Side-note: the scoped-reset safety net is covered by
``test_reset_demo_scope.py`` and is invoked here only for the reset+seed
integration path, not re-asserted.
"""
from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

User = get_user_model()


# ──────────────────────────── fixtures ────────────────────────────────


@pytest.fixture
def run_seed():
    """Call the management command, capturing stdout for inspection."""

    def _call(*args: str) -> str:
        out = StringIO()
        call_command("seed_demo", *args, stdout=out, verbosity=0)
        return out.getvalue()

    return _call


# ──────────────────────── full-run aggregate tests ─────────────────────


@pytest.mark.django_db
def test_seed_demo_creates_plan_aggregates(run_seed):
    """Fresh run creates the exact per-plan headcount and content counts."""
    from apps.apartments.models import Building, Entrance, Unit
    from apps.issues.models import Issue
    from apps.passes.models import VehiclePass
    from apps.posts.models import Announcement, Post
    from apps.ratings.models import Rating

    run_seed()

    # § 3 — PR-13 alignment: 1 apartment block + 1 cottage,
    # 4 entrances total (А, Б, В, Котедж), 49 units (48 apartments + 1 cottage).
    assert Building.objects.filter(name="Зелений Квартал — Демо").count() == 1
    assert Building.objects.filter(
        name="Зелений Квартал — Демо · Котедж"
    ).count() == 1
    assert Entrance.objects.count() == 4
    assert Unit.objects.count() == 49

    # § 4 — PR-13 alignment: 47 demo users total
    # (2 + 3 + 8 + 32 = 45 base, +1 renter, +1 cottage_owner).
    assert User.objects.filter(email__iendswith="@demo.com").count() == 47

    # § 5 — 45 issues with the planned status mix.
    assert Issue.objects.count() == 45
    by_status = {
        s: Issue.objects.filter(status=s).count()
        for s in ("reported", "accepted", "in_progress", "done", "rejected")
    }
    assert by_status == {
        "reported": 12,
        "accepted": 10,
        "in_progress": 8,
        "done": 10,
        "rejected": 5,
    }
    assert Issue.objects.filter(priority="high").count() == 7

    # § 5.3 — ≥ 3 overdue, but only among *active* states (plan intent).
    active_overdue = sum(
        1
        for issue in Issue.objects.filter(
            status__in=("reported", "accepted", "in_progress")
        )
        if issue.is_overdue
    )
    assert active_overdue >= 3

    # § 6 — 18 posts + 5 announcements.
    assert Post.objects.count() == 18
    assert Announcement.objects.count() == 5

    # § 8 — 22 vehicle passes.
    assert VehiclePass.objects.count() == 22

    # § 9 — 35 worker ratings.
    assert Rating.objects.count() == 35


@pytest.mark.django_db
def test_seed_demo_is_idempotent(run_seed):
    """Second invocation creates zero new rows — natural keys hold."""
    from apps.issues.models import Issue
    from apps.passes.models import VehiclePass
    from apps.posts.models import Announcement, Post
    from apps.ratings.models import Rating

    run_seed()
    snapshot = {
        "users": User.objects.count(),
        "issues": Issue.objects.count(),
        "posts": Post.objects.count(),
        "announcements": Announcement.objects.count(),
        "passes": VehiclePass.objects.count(),
        "ratings": Rating.objects.count(),
    }

    run_seed()

    assert User.objects.count() == snapshot["users"]
    assert Issue.objects.count() == snapshot["issues"]
    assert Post.objects.count() == snapshot["posts"]
    assert Announcement.objects.count() == snapshot["announcements"]
    assert VehiclePass.objects.count() == snapshot["passes"]
    assert Rating.objects.count() == snapshot["ratings"]


@pytest.mark.django_db
def test_seed_demo_reset_then_seed_restores_aggregates(run_seed):
    """``--reset`` wipes the demo scope, follow-up seed rebuilds it."""
    from apps.issues.models import Issue
    from apps.ratings.models import Rating

    run_seed()
    assert Issue.objects.count() == 45

    # Reset-only: the seed phase is part of the same command, so after
    # --reset the aggregates should still match plan numbers.
    run_seed("--reset")
    assert Issue.objects.filter(status="reported").count() == 12
    assert Issue.objects.count() == 45
    assert Rating.objects.count() == 35


# ────────────────────────── CLI safety paths ─────────────────────────


@pytest.mark.django_db
def test_dry_run_without_reset_is_rejected():
    """``--dry-run`` alone is a user error — we fail loudly."""
    with pytest.raises(CommandError, match="--dry-run only applies"):
        call_command("seed_demo", "--dry-run", verbosity=0)


@pytest.mark.django_db
def test_dry_run_with_reset_does_not_seed(run_seed):
    """``--reset --dry-run`` reports scope but never mutates the DB."""
    from apps.apartments.models import Building
    from apps.issues.models import Issue

    # Pre-seed so reset has something to report.
    run_seed()
    before_users = User.objects.count()
    before_issues = Issue.objects.count()

    output = run_seed("--reset", "--dry-run")

    assert "dry-run" in output
    assert User.objects.count() == before_users
    assert Issue.objects.count() == before_issues
    assert Building.objects.filter(name="Зелений Квартал — Демо").exists()


@pytest.mark.django_db
def test_passwords_from_env_requires_env_var(monkeypatch):
    """Prod flag without ``DEMO_PASSWORD`` is a hard failure, never silent."""
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    with pytest.raises(CommandError, match="DEMO_PASSWORD env var"):
        call_command("seed_demo", "--passwords-from-env", verbosity=0)


@pytest.mark.django_db
def test_passwords_from_env_rejects_short_password(monkeypatch):
    """< 8 char passwords are rejected before the seed phase runs."""
    monkeypatch.setenv("DEMO_PASSWORD", "short")
    with pytest.raises(CommandError, match="≥ 8 characters"):
        call_command("seed_demo", "--passwords-from-env", verbosity=0)


@pytest.mark.django_db
def test_passwords_from_env_uses_env_value(monkeypatch, run_seed):
    """Env var value is applied to seeded users when the flag is set."""
    monkeypatch.setenv("DEMO_PASSWORD", "CustomProdPass1!")
    run_seed("--passwords-from-env")

    dispatcher = User.objects.get(email="dispatcher@demo.com")
    assert dispatcher.check_password("CustomProdPass1!")
    assert not dispatcher.check_password("Demo1234!")


# ─────────────────── negative coverage — scope isolation ──────────────


@pytest.mark.django_db
def test_seed_demo_does_not_touch_non_demo_users(run_seed):
    """Reset+seed preserves non-demo users (real operators)."""
    real_user = User.objects.create_user(
        username="real-operator",
        email="operator@real-company.com",
        password="Secret1234!",
    )

    run_seed("--reset")  # triggers reset → seed in one command

    real_user.refresh_from_db()
    assert real_user.is_active
    assert real_user.email == "operator@real-company.com"


@pytest.mark.django_db
def test_seed_demo_preserves_superusers(run_seed):
    """Superusers are untouchable even if they somehow share the demo domain."""
    admin = User.objects.create_superuser(
        username="rootadmin",
        email="root@demo.com",  # intentionally in scope
        password="RootPass1234!",
    )

    run_seed("--reset")

    admin.refresh_from_db()
    assert admin.is_superuser
    assert admin.is_active


# ───────────────────────── PR-13: concept alignment ──────────────────────────


@pytest.mark.django_db
def test_seed_demo_creates_organization_linked_to_building(run_seed):
    """PR-13: the demo ОСББ exists, is ``SINGLE_BUILDING``, owns the buildings."""
    from apps.apartments.models import Building
    from apps.organizations.models import Organization, OrganizationType

    run_seed()

    org = Organization.objects.get(name="ОСББ «Зелений Квартал — Демо»")
    assert org.type == OrganizationType.SINGLE_BUILDING
    assert org.is_demo is True
    assert org.is_active is True

    # Both buildings link to the org.
    apartment = Building.objects.get(name="Зелений Квартал — Демо")
    cottage = Building.objects.get(name="Зелений Квартал — Демо · Котедж")
    assert apartment.organization_id == org.pk
    assert cottage.organization_id == org.pk


@pytest.mark.django_db
def test_seed_demo_cottage_is_a_cottage(run_seed):
    """PR-13: the second Building is ``type=COTTAGE`` with exactly one Unit."""
    from apps.apartments.models import Building, BuildingType, Entrance, Unit

    run_seed()

    cottage = Building.objects.get(name="Зелений Квартал — Демо · Котедж")
    assert cottage.type == BuildingType.COTTAGE
    assert cottage.total_area is not None
    assert cottage.total_area > 0

    entrances = Entrance.objects.filter(building=cottage)
    assert entrances.count() == 1
    units = Unit.objects.filter(entrance__building=cottage)
    assert units.count() == 1
    assert units.first().area == cottage.total_area


@pytest.mark.django_db
def test_seed_demo_apartment_units_have_area(run_seed):
    """Every apartment Unit carries a realistic m² area."""
    from apps.apartments.models import Building, Unit

    run_seed()

    apartment = Building.objects.get(name="Зелений Квартал — Демо")
    units = Unit.objects.filter(entrance__building=apartment)
    assert units.count() == 48
    # Every unit has area set.
    assert units.filter(area__isnull=True).count() == 0
    # Areas sit in a realistic range for Kyiv apartments (>40 m², <130 m²).
    assert units.filter(area__lt=40).count() == 0
    assert units.filter(area__gt=130).count() == 0


@pytest.mark.django_db
def test_seed_demo_creates_multi_unit_owner(run_seed):
    """One resident holds two Residencies — exactly one primary."""
    from apps.apartments.models import Residency

    run_seed()

    # resident3 is the designated multi-unit owner in seed_users.
    resident3 = User.objects.get(email="resident3@demo.com")
    residencies = Residency.objects.filter(user=resident3)
    assert residencies.count() == 2
    assert residencies.filter(is_primary=True).count() == 1
    assert residencies.filter(is_primary=False).count() == 1


@pytest.mark.django_db
def test_seed_demo_creates_tenant_role_residency(run_seed):
    """A dedicated renter user holds a Residency with role=TENANT."""
    from apps.apartments.models import Residency, ResidencyRole

    run_seed()

    renter = User.objects.get(email="renter@demo.com")
    residency = Residency.objects.get(user=renter, is_primary=True)
    assert residency.role == ResidencyRole.TENANT
    assert residency.start_date is not None


@pytest.mark.django_db
def test_seed_demo_creates_turnover_residency_with_end_date(run_seed):
    """At least one Residency carries ``end_date`` — the turnover demo row."""
    from apps.apartments.models import Residency

    run_seed()

    closed = Residency.objects.filter(end_date__isnull=False)
    assert closed.exists(), "No Residency with end_date — turnover demo missing"
    row = closed.first()
    # Sanity: end_date is after start_date (model.clean() asserts this too).
    assert row.end_date >= row.start_date


@pytest.mark.django_db
def test_seed_demo_creates_cottage_owner_bound_to_cottage(run_seed):
    """The cottage@demo.com user has a primary Residency on the cottage unit."""
    from apps.apartments.models import BuildingType, Residency

    run_seed()

    cottage_owner = User.objects.get(email="cottage@demo.com")
    residency = Residency.objects.get(user=cottage_owner, is_primary=True)
    assert residency.unit.entrance.building.type == BuildingType.COTTAGE


@pytest.mark.django_db
def test_seed_demo_primary_residencies_have_start_date(run_seed):
    """Every primary Residency carries a ``start_date`` (no NULLs allowed)."""
    from apps.apartments.models import Residency

    run_seed()

    missing = Residency.objects.filter(is_primary=True, start_date__isnull=True)
    assert missing.count() == 0, (
        "Primary Residencies without start_date: "
        f"{list(missing.values_list('user__email', flat=True))}"
    )
