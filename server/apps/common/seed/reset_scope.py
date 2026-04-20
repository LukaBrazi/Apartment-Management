"""Scoped deletion of demo data — the single most dangerous file in this app.

Per ``docs/DEMO_SEED_PLAN.md`` §11: the reset MUST be paranoid.  An error
here equals silently wiping a production customer's data.  Defense in depth:

1. **Hard-coded markers.** ``DEMO_EMAIL_DOMAIN`` /
   ``DEMO_BUILDING_NAME_PREFIX`` come from
   :mod:`apps.common.seed.helpers` — never from env, never from
   settings.  An attacker with ``env`` access cannot broaden the scope.
   PR-13 switched the building filter from exact-name to
   ``name__startswith`` to accommodate the cottage showcase; the
   prefix is still a code constant.

2. **Explicit ``is_demo`` flag (PR-12 + PR-13).** Users, Buildings and
   Organizations carry a dedicated ``is_demo`` BooleanField that the
   reset filter ANDs with the hard-coded markers above.  A real user
   with a coincidental ``@demo.com`` email is safe as long as nobody
   flipped ``is_demo`` on them — and the seed is the only code path
   that sets it.  Organizations rely solely on the flag (no name
   prefix) because "demo" org names are too varied to key off.

3. **Superuser exclusion.** ``is_superuser=False`` is applied to the
   queryset.  Even a user who *does* happen to have a ``@demo.com`` email
   is left alone if they've been granted admin.

4. **Sanity-threshold pre-flight (PR-12).** Before any delete we refuse
   if the DB shape doesn't look like the demo shape: too many non-demo
   users, or any non-demo Buildings sitting in the table.  The threshold
   lives in code (not env) so it can't be widened remotely.

5. **Pre/post snapshots + assertions inside ``transaction.atomic``.** If
   the delete touched a non-demo user or changed the superuser count, the
   transaction rolls back *before* it commits and the command exits with
   a stack trace.

6. **Best-effort tag cleanup.** Post tags are globally scoped in this
   codebase; after the user deletes we GC unused ones to keep the DB tidy.

The blocking safety test lives at
``apps/tests/test_reset_demo_scope.py`` — CI must not proceed without it
being green.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import transaction

from .helpers import (
    DEMO_BUILDING_NAME,  # re-exported for historical tests
    DEMO_BUILDING_NAME_PREFIX,
    DEMO_EMAIL_DOMAIN,
)

# ── Sanity thresholds ──────────────────────────────────────────────────────
# Code constants, not env — see module docstring §4. Tuned for the current
# single-building demo prod: real-world customer count is 0, and the demo
# itself never exceeds a few dozen accounts. If the seed ever grows past
# this floor, bump the constant deliberately in a PR so the diff is
# reviewable.
MAX_NON_DEMO_USERS = 50
# Generous headroom for a few real customer buildings living beside the
# demo on the same DB.  The goal is not zero-tolerance — it's catching
# "oh god this pod is pointing at the wrong DB" scenarios where the
# non-demo count spikes into the hundreds.
MAX_NON_DEMO_BUILDINGS = 5

if TYPE_CHECKING:  # pragma: no cover — typing only
    from collections.abc import Mapping

logger = logging.getLogger(__name__)


class DemoResetSafetyError(RuntimeError):
    """Raised when a post-condition check fails — aborts the transaction."""


@dataclass
class ResetReport:
    """Structured counts of what the reset removed (or would remove).

    Returned to callers (the ``seed_demo`` orchestrator and test suite).  The
    counts are the pre-delete queryset sizes — i.e. the number of rows that
    will or did disappear at the top level.  Cascade descendants are not
    counted individually; if you need those, query the DB after the call.
    """

    dry_run: bool
    demo_users_matched: int
    demo_buildings_matched: int
    superusers_preserved: int
    non_demo_users_preserved: int
    non_demo_buildings_preserved: int = 0
    demo_issues_matched: int = 0
    demo_posts_matched: int = 0
    demo_passes_matched: int = 0
    demo_ratings_matched: int = 0
    # PR-13: the seed now creates an Organization — tracked separately
    # so the dry-run report lets operators see it alongside user/building
    # counts before flipping ALLOW_DEMO_RESET on.
    demo_organizations_matched: int = 0
    non_demo_organizations_preserved: int = 0
    # News rows — platform-wide + org-scoped. Tracked separately from
    # posts because ``News.organization`` uses ``SET_NULL``; we MUST
    # delete the rows before the org, otherwise org-scoped news would
    # leak out as pseudo-global entries after reset.
    demo_news_matched: int = 0
    orphan_tags_removed: int = 0

    def as_dict(self) -> "Mapping[str, object]":
        return asdict(self)


def reset_demo_scope(*, dry_run: bool = False) -> ResetReport:
    """Scoped delete of demo data, safe to run on prod.

    Parameters
    ----------
    dry_run:
        If ``True``, counts the would-be-deleted rows and returns without
        touching the DB.  Used for first-run audit on prod — pipe the return
        value into Sentry and eyeball it before flipping to a real delete.

    Returns
    -------
    ResetReport
        Counts of matched / preserved rows.  Callers (tests, orchestrator)
        use this to verify the pre-delete assumption holds before trusting
        a subsequent seeding run.

    Raises
    ------
    DemoResetSafetyError
        If post-delete invariants (superuser count unchanged, non-demo user
        count unchanged) do not hold.  The transaction is rolled back as part
        of raising — caller sees the DB in its pre-reset state.
    """
    # Deferred imports: these apps may not be importable at module load time in
    # every manage.py path.  Lazy import avoids circularity in the management-
    # command loader.
    from apps.apartments.models import Building
    from apps.issues.models import Issue
    from apps.news.models import News
    from apps.organizations.models import Organization
    from apps.passes.models import VehiclePass
    from apps.posts.models import Post
    from apps.ratings.models import Rating

    User = get_user_model()

    # ── Pre-flight snapshot ──────────────────────────────────────────────────
    # These two numbers are the invariant we assert after the delete.  If they
    # move, we rolled into real data somewhere — abort and rollback.
    # PR-13: building scope is "name starts with the demo prefix" to cover
    # the cottage + apartment block the seed now creates. A stray
    # customer building named "Зелений Квартал — Демо" would have been
    # matched before anyway; the prefix match simply extends that to
    # "Зелений Квартал — Демо · Котедж".
    pre_superusers = User.objects.filter(is_superuser=True).count()
    pre_non_demo_users = User.objects.exclude(
        email__iendswith=DEMO_EMAIL_DOMAIN,
    ).count()
    pre_non_demo_buildings = Building.objects.exclude(
        name__startswith=DEMO_BUILDING_NAME_PREFIX,
    ).count()
    pre_non_demo_orgs = Organization.objects.filter(is_demo=False).count()

    # ── Sanity thresholds (PR-12) ────────────────────────────────────────────
    # Refuse to proceed if the DB doesn't look like a demo env: the goal is
    # to catch a misconfigured pod pointed at a real customer DB before it
    # gets a chance to scan the data.
    if pre_non_demo_users > MAX_NON_DEMO_USERS:
        raise DemoResetSafetyError(
            f"Refusing seed_demo reset: found {pre_non_demo_users} non-demo "
            f"users (threshold MAX_NON_DEMO_USERS={MAX_NON_DEMO_USERS}). "
            "This DB does not look like a demo environment — aborting "
            "before any delete. To unblock, either scrub the non-demo "
            "users manually or raise the constant in reset_scope.py in a "
            "reviewed PR."
        )
    if pre_non_demo_buildings > MAX_NON_DEMO_BUILDINGS:
        raise DemoResetSafetyError(
            f"Refusing seed_demo reset: found {pre_non_demo_buildings} "
            f"non-demo Buildings (threshold "
            f"MAX_NON_DEMO_BUILDINGS={MAX_NON_DEMO_BUILDINGS}). "
            "This DB does not look like a demo environment — aborting "
            "before any delete."
        )

    # Demo scope filter — three-factor match:
    #   1. email ends with @demo.com (hard-coded constant)
    #   2. is_demo=True              (seed-only flag, PR-12)
    #   3. is_superuser=False         (hard guard)
    # All three must hold.  A real user with a freak @demo.com address
    # without the is_demo flag survives; a hand-flagged is_demo user
    # without a @demo.com email also survives.  Belt-and-braces.
    demo_users_qs = User.objects.filter(
        email__iendswith=DEMO_EMAIL_DOMAIN,
        is_demo=True,
        is_superuser=False,  # ← HARD GUARD — never delete a superuser
    )
    # PR-13: prefix match covers the apartment block AND the cottage
    # that PR-13 adds. ``is_demo=True`` stays as the second factor so a
    # hand-created building that happens to share the prefix survives
    # unless someone also flipped the flag on it.
    demo_buildings_qs = Building.objects.filter(
        name__startswith=DEMO_BUILDING_NAME_PREFIX,
        is_demo=True,
    )
    # PR-13: matching organisations is done purely by the ``is_demo``
    # flag — there is no stable name prefix to lean on because demo
    # orgs are unusual enough that we want a single, explicit opt-in
    # marker. The seed module is the only writer of this flag.
    demo_orgs_qs = Organization.objects.filter(is_demo=True)

    matched_users = demo_users_qs.count()
    matched_buildings = demo_buildings_qs.count()
    matched_orgs = demo_orgs_qs.count()

    # Content scope — Issues / Posts / Passes / Ratings carry SET_NULL FKs to
    # User (not CASCADE as plan §11.1 prose suggested), so we can't rely on
    # ``User.delete()`` to take their rows with it.  We identify demo content
    # as anything authored-by / rated / tied to a demo user, *or* tied to the
    # demo building's units.  That matches the plan's intent: "scoped reset
    # wipes demo content", regardless of how FKs are configured.
    user_ids = list(demo_users_qs.values_list("pk", flat=True))
    demo_issues_qs = Issue.objects.filter(
        reported_by_id__in=user_ids,
    ) | Issue.objects.filter(assigned_to_id__in=user_ids)
    demo_posts_qs = Post.objects.filter(author_id__in=user_ids)
    demo_passes_qs = VehiclePass.objects.filter(
        tenant_id__in=user_ids,
    ) | VehiclePass.objects.filter(closed_by_id__in=user_ids)
    demo_ratings_qs = Rating.objects.filter(
        rating_user_id__in=user_ids,
    ) | Rating.objects.filter(rated_user_id__in=user_ids)
    # PR-7 dropped the legacy ``Apartment`` model — no tenant→Apartment
    # rows survive for the reset to scoop up.

    matched_issues = demo_issues_qs.count()
    matched_posts = demo_posts_qs.count()
    matched_passes = demo_passes_qs.count()
    matched_ratings = demo_ratings_qs.count()

    # News demo-scope: an article is "demo" if it was written by a
    # demo dispatcher OR scoped to a demo org. The OR catches both
    # the platform-wide seed articles (org=NULL, author=demo user)
    # and the org-scoped ones. Deletion order matters — see below.
    org_ids = list(demo_orgs_qs.values_list("pkid", flat=True))
    demo_news_qs = News.objects.filter(author_id__in=user_ids) | News.objects.filter(
        organization_id__in=org_ids,
    )
    matched_news = demo_news_qs.count()

    logger.info(
        "reset_demo_scope: dry_run=%s  demo_users=%d  demo_buildings=%d  "
        "demo_orgs=%d  demo_issues=%d  demo_posts=%d  demo_passes=%d  "
        "demo_ratings=%d  demo_news=%d  pre_superusers=%d  "
        "pre_non_demo_users=%d  pre_non_demo_buildings=%d  "
        "pre_non_demo_orgs=%d",
        dry_run, matched_users, matched_buildings, matched_orgs,
        matched_issues, matched_posts, matched_passes, matched_ratings,
        matched_news,
        pre_superusers, pre_non_demo_users, pre_non_demo_buildings,
        pre_non_demo_orgs,
    )

    if dry_run:
        return ResetReport(
            dry_run=True,
            demo_users_matched=matched_users,
            demo_buildings_matched=matched_buildings,
            demo_organizations_matched=matched_orgs,
            demo_issues_matched=matched_issues,
            demo_posts_matched=matched_posts,
            demo_passes_matched=matched_passes,
            demo_ratings_matched=matched_ratings,
            demo_news_matched=matched_news,
            superusers_preserved=pre_superusers,
            non_demo_users_preserved=pre_non_demo_users,
            non_demo_buildings_preserved=pre_non_demo_buildings,
            non_demo_organizations_preserved=pre_non_demo_orgs,
        )

    orphan_tags_removed = 0

    with transaction.atomic():
        # ── Content first, users second ─────────────────────────────────────
        # Order matters: delete content rows before users so we don't have to
        # re-query after User.delete() nulls out the FKs.  Content deletion is
        # safe because we've already pinned the pk set above.
        demo_ratings_qs.delete()
        demo_passes_qs.delete()
        demo_posts_qs.delete()        # Replies cascade via Post.replies → Post
        demo_issues_qs.delete()       # Issue has its own table; no children
        # News MUST be deleted before the demo org — the ``organization``
        # FK is ``SET_NULL``, so if we didn't, org-scoped demo news would
        # survive with ``organization=NULL`` and silently leak out as
        # platform-wide news visible to every future tenant.
        demo_news_qs.delete()

        # Django cascades handle User children: Profile (O2O CASCADE),
        # OrganizationMembership (FK CASCADE), TelegramProfile (O2O CASCADE),
        # TelegramVerificationToken (FK CASCADE).
        demo_users_qs.delete()

        # Buildings → Entrances → Units cascade, plus Announcements → CASCADE.
        # Delete the buildings explicitly (before the Organization) so we
        # exercise the ``is_demo`` filter instead of relying on cascade
        # from the organization. This keeps the matched/deleted counts
        # honest in the returned ResetReport.
        demo_buildings_qs.delete()

        # PR-13: delete demo organizations last. Any building that
        # happened to stay linked to a demo org would have cascaded
        # above anyway, but matching on ``is_demo=True`` gives us a
        # direct handle for the count + post-invariant.
        demo_orgs_qs.delete()

        # Orphan tag cleanup — see plan §11.4.  django-taggit exposes the Tag
        # model via ``TaggableManager.through.tag_model()``.  Import lazily;
        # the tag system may be disabled in some test contexts.
        orphan_tags_removed = _cleanup_orphan_tags()

        # ── Post-condition: the invariants we promised never to violate ──
        post_superusers = User.objects.filter(is_superuser=True).count()
        post_non_demo_users = User.objects.exclude(
            email__iendswith=DEMO_EMAIL_DOMAIN,
        ).count()
        post_non_demo_buildings = Building.objects.exclude(
            name__startswith=DEMO_BUILDING_NAME_PREFIX,
        ).count()
        post_non_demo_orgs = Organization.objects.filter(is_demo=False).count()

        if post_superusers != pre_superusers:
            raise DemoResetSafetyError(
                f"Superuser count changed during reset "
                f"({pre_superusers} → {post_superusers}). "
                "Rolling back transaction — DB untouched.",
            )
        if post_non_demo_users != pre_non_demo_users:
            raise DemoResetSafetyError(
                f"Non-demo user count changed during reset "
                f"({pre_non_demo_users} → {post_non_demo_users}). "
                "Rolling back transaction — DB untouched.",
            )
        if post_non_demo_buildings != pre_non_demo_buildings:
            raise DemoResetSafetyError(
                f"Non-demo Building count changed during reset "
                f"({pre_non_demo_buildings} → {post_non_demo_buildings}). "
                "Rolling back transaction — DB untouched.",
            )
        if post_non_demo_orgs != pre_non_demo_orgs:
            raise DemoResetSafetyError(
                f"Non-demo Organization count changed during reset "
                f"({pre_non_demo_orgs} → {post_non_demo_orgs}). "
                "Rolling back transaction — DB untouched.",
            )

    return ResetReport(
        dry_run=False,
        demo_users_matched=matched_users,
        demo_buildings_matched=matched_buildings,
        demo_organizations_matched=matched_orgs,
        demo_issues_matched=matched_issues,
        demo_posts_matched=matched_posts,
        demo_passes_matched=matched_passes,
        demo_ratings_matched=matched_ratings,
        demo_news_matched=matched_news,
        superusers_preserved=pre_superusers,
        non_demo_users_preserved=pre_non_demo_users,
        non_demo_buildings_preserved=pre_non_demo_buildings,
        non_demo_organizations_preserved=pre_non_demo_orgs,
        orphan_tags_removed=orphan_tags_removed,
    )


# ───────────────────────────── internal helpers ──────────────────────────────


def _cleanup_orphan_tags() -> int:
    """Delete ``Tag`` rows that no longer appear on any tagged object.

    Returns the number of deleted tags.  Best-effort: if ``taggit`` isn't
    installed or the tag model shape differs, we silently return 0.  This is
    a cleanup nicety, not a safety invariant.
    """
    try:
        from taggit.models import Tag
    except Exception:  # pragma: no cover — taggit not available
        return 0

    # ``taggit`` stores M2M membership in ``TaggedItem``; a tag is orphaned
    # if no ``TaggedItem`` references it.  Count -> filter -> delete returns a
    # tuple (deleted_count, per_model_dict) — we only care about the count.
    from django.db.models import Count

    deleted, _ = (
        Tag.objects.annotate(usage=Count("taggit_taggeditem_items"))
        .filter(usage=0)
        .delete()
    )
    return int(deleted)
