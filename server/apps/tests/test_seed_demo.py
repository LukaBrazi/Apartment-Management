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

    # § 3 — one building, three entrances, 48 units.
    assert Building.objects.filter(name="Зелений Квартал — Демо").count() == 1
    assert Entrance.objects.count() == 3
    assert Unit.objects.count() == 48

    # § 4 — 45 demo users total (2 + 3 + 8 + 32).
    assert User.objects.filter(email__iendswith="@demo.com").count() == 45

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
