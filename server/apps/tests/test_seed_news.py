"""Unit + integration tests for ``apps.common.seed.seed_news``.

These tests live alongside the other seed-module tests and follow
their shape: each one calls the seed function directly with minimal
fixtures, asserting what the orchestrator downstream will rely on
(categories present, news rows with the right org scoping, covers
non-empty, idempotent re-run).

A separate smoke test exercises the full ``seed_demo`` integration
path — i.e. running the management command and checking ``News``
count — to catch wiring regressions (missing import, wrong call
site) that unit tests alone would let through.

We also assert the reset-scope behavior for News: org-scoped demo
news MUST be deleted by ``reset_demo_scope``, not left behind with
``organization=NULL`` thanks to the FK's ``SET_NULL``. That leak
would silently expose old-tenant news as platform-wide entries.
"""
from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command


# ──────────────────────────── fixtures ────────────────────────────────


@pytest.fixture
def seeded_prereqs(db):
    """Run only the prereq seed modules (org + building + users).

    ``seed_news`` needs a dispatcher (for ``author``) and an org
    (for the ``organization`` FK). Building isn't strictly required
    by the News model, but ``seed_users`` depends on it.
    """
    from apps.common.seed import (
        seed_building,
        seed_organization,
        seed_users,
    )
    from apps.common.seed.helpers import DEFAULT_DEMO_PASSWORD, init_random

    init_random()
    org_result = seed_organization.seed()
    building_result = seed_building.seed(organization_result=org_result)
    # Keep residents_count small — seed_news only needs one dispatcher.
    users_result = seed_users.seed(
        building_result=building_result,
        organization_result=org_result,
        residents_count=4,
        password=DEFAULT_DEMO_PASSWORD,
    )
    return {
        "org_result": org_result,
        "building_result": building_result,
        "users_result": users_result,
    }


# ──────────────────────── unit tests ───────────────────────────────────


@pytest.mark.django_db
class TestSeedNews:
    def test_creates_categories(self, seeded_prereqs):
        from apps.common.seed import seed_news
        from apps.news.models import NewsCategory

        result = seed_news.seed(
            users_result=seeded_prereqs["users_result"],
            organization_result=seeded_prereqs["org_result"],
        )

        # All 5 categories from CATEGORY_SPECS must end up in the DB.
        assert NewsCategory.objects.count() >= 5
        assert result.categories_created == 5

        # Named check — downstream UI expects these exact names on
        # the category-pill badge.
        names = set(NewsCategory.objects.values_list("name", flat=True))
        assert {"Оголошення", "Сервіс", "Події", "Ремонт", "Безпека"}.issubset(names)

    def test_creates_news_mix_global_and_org_scoped(self, seeded_prereqs):
        from apps.common.seed import seed_news
        from apps.news.models import News

        result = seed_news.seed(
            users_result=seeded_prereqs["users_result"],
            organization_result=seeded_prereqs["org_result"],
        )

        total = News.objects.count()
        assert total == result.news_created
        assert total >= 5  # default spec has 10, minimum we want is 5

        # Sanity: at least some platform-wide (org IS NULL) so every
        # tenant sees a baseline — this is what fixed the original
        # "tenant sees empty /news" bug.
        global_count = News.objects.filter(organization__isnull=True).count()
        org_count = News.objects.filter(
            organization=seeded_prereqs["org_result"].organization,
        ).count()
        assert global_count >= 1, "expected at least one platform-wide news row"
        assert org_count >= 1, "expected at least one org-scoped news row"
        assert global_count + org_count == total

    def test_at_least_one_pinned(self, seeded_prereqs):
        from apps.common.seed import seed_news
        from apps.news.models import News

        seed_news.seed(
            users_result=seeded_prereqs["users_result"],
            organization_result=seeded_prereqs["org_result"],
        )

        assert News.objects.filter(pinned=True).exists(), (
            "at least one pinned article is required to exercise the "
            "'-pinned, -published_at' ordering in NewsListAPIView"
        )

    def test_covers_generated(self, seeded_prereqs):
        """Pillow-generated covers must be attached to every new row."""
        from apps.common.seed import seed_news
        from apps.news.models import News

        result = seed_news.seed(
            users_result=seeded_prereqs["users_result"],
            organization_result=seeded_prereqs["org_result"],
        )

        # covers_generated tracks successful Pillow saves; must match
        # the number of newly-created rows on a fresh run.
        assert result.covers_generated == result.news_created

        for news in News.objects.all():
            assert news.cover_image and news.cover_image.name, (
                f"News {news.title!r} has no cover image attached"
            )

    def test_all_published(self, seeded_prereqs):
        """Seed must produce published rows; drafts would stay invisible."""
        from apps.common.seed import seed_news
        from apps.news.models import News

        seed_news.seed(
            users_result=seeded_prereqs["users_result"],
            organization_result=seeded_prereqs["org_result"],
        )

        assert News.objects.filter(is_published=False).count() == 0

    def test_idempotent_rerun(self, seeded_prereqs):
        """Second call must NOT create duplicate rows (natural key: title)."""
        from apps.common.seed import seed_news
        from apps.news.models import News

        seed_news.seed(
            users_result=seeded_prereqs["users_result"],
            organization_result=seeded_prereqs["org_result"],
        )
        baseline = News.objects.count()

        result2 = seed_news.seed(
            users_result=seeded_prereqs["users_result"],
            organization_result=seeded_prereqs["org_result"],
        )

        assert News.objects.count() == baseline
        assert result2.news_created == 0
        assert result2.news_skipped == baseline

    def test_skips_when_no_dispatchers(self, db):
        """Seed must degrade gracefully when there's no author to use."""
        from apps.common.seed import (
            seed_building,
            seed_news,
            seed_organization,
        )
        from apps.common.seed.seed_users import UsersSeedResult

        org_result = seed_organization.seed()
        seed_building.seed(organization_result=org_result)
        # Synthesise an empty UsersSeedResult (no dispatchers) — this
        # is the degenerate case the module must not crash on.
        empty_users = UsersSeedResult()

        result = seed_news.seed(
            users_result=empty_users,
            organization_result=org_result,
        )

        assert result.news_created == 0
        assert result.covers_generated == 0


# ──────────────────────── integration ──────────────────────────────────


@pytest.mark.django_db
def test_seed_demo_creates_news(db):
    """Full ``seed_demo`` run wires News correctly end-to-end.

    Guards against someone bumping the import but forgetting the
    ``.seed(...)`` call in the orchestrator, or vice versa.
    """
    from apps.news.models import News, NewsCategory

    out = StringIO()
    call_command("seed_demo", stdout=out, verbosity=0)

    assert News.objects.count() > 0, (
        "seed_demo must create News rows — the original bug was that "
        "tenants saw an empty /news page because no rows ever existed"
    )
    assert NewsCategory.objects.count() >= 5

    # Output includes a "news: +N" line.
    captured = out.getvalue()
    assert "news:" in captured


# ──────────────────────── reset-scope interaction ──────────────────────


@pytest.mark.django_db
def test_reset_deletes_org_scoped_news(seeded_prereqs):
    """``reset_demo_scope`` must delete org-scoped demo news.

    Regression guard: ``News.organization`` is ``SET_NULL``, so if the
    reset deleted the demo Organization without first deleting the
    org-scoped news, those rows would survive with ``organization=NULL``
    and silently start showing up as platform-wide news to every
    future tenant of every future org. That's an information leak.
    """
    from apps.common.seed import seed_news
    from apps.common.seed.reset_scope import reset_demo_scope
    from apps.news.models import News

    seed_news.seed(
        users_result=seeded_prereqs["users_result"],
        organization_result=seeded_prereqs["org_result"],
    )
    assert News.objects.count() > 0

    report = reset_demo_scope(dry_run=False)

    # No demo news must remain — neither org-scoped nor platform-wide
    # (because the platform-wide ones are authored by a demo user).
    assert News.objects.count() == 0
    # The report surfaces the matched count so operators see it.
    assert report.demo_news_matched > 0
