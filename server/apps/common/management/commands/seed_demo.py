"""Seed the ApartmentOS demo dataset for «Зелений Квартал — Демо».

This command is the single entry point for creating (or refreshing) the
demo data that customer-facing environments serve — and, optionally, for
resetting that data first.

Design (plan ``docs/DEMO_SEED_PLAN.md``):

* All heavy lifting is delegated to modules in
  :mod:`apps.common.seed` — the orchestrator itself owns only CLI
  parsing, module sequencing, password sourcing, and the
  reset-before-seed pipeline.
* Idempotent by default: rerunning without ``--reset`` updates/inserts
  only what's missing.
* Scoped reset: ``--reset`` deletes demo rows only, via
  :func:`apps.common.seed.reset_scope.reset_demo_scope`, which is
  unit-tested to never touch real users or superusers (see
  ``apps/tests/test_reset_demo_scope.py``).
* Prod calls MUST pass ``--passwords-from-env`` so the ``Demo1234!``
  default stays out of customer environments.

Example invocations
-------------------

Local dev (uses the default ``Demo1234!`` password)::

    python manage.py seed_demo

CI smoke (thinner fixture)::

    python manage.py seed_demo --residents-count=12 --issues-count=20 \
        --posts-count=8 --passes-count=10

Prod nightly (via K8s CronJob)::

    python manage.py seed_demo --reset --passwords-from-env

Dry-run audit before the first prod invocation::

    python manage.py seed_demo --reset --dry-run
"""
from __future__ import annotations

import os
import sys
from dataclasses import asdict

from django.core.management.base import BaseCommand, CommandError

from apps.common.seed import (
    reset_scope,
    seed_building,
    seed_issues,
    seed_passes,
    seed_posts,
    seed_ratings,
    seed_users,
)
from apps.common.seed.helpers import DEFAULT_DEMO_PASSWORD, init_random


class Command(BaseCommand):
    help = (
        "Seed the ApartmentOS demo dataset (plan docs/DEMO_SEED_PLAN.md). "
        "With --reset, first scoped-deletes existing demo rows."
    )

    def add_arguments(self, parser) -> None:  # noqa: D401
        """Register CLI flags — mirror plan §10.1."""
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete demo-scoped rows (users @demo.com, demo Building) before seeding.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Only report what would be deleted by --reset; does nothing "
                "to the DB.  Ignored when --reset is not set."
            ),
        )
        parser.add_argument(
            "--passwords-from-env",
            action="store_true",
            help=(
                "Read seed password from the DEMO_PASSWORD env var. "
                "Required on production deploys — falls back to the "
                "documented dev default otherwise."
            ),
        )
        parser.add_argument(
            "--residents-count",
            type=int,
            default=32,
            help="Total residents to create (min 4; plan default 32).",
        )
        parser.add_argument(
            "--issues-count",
            type=int,
            default=45,
            help="Total Issues to create (min 5; plan default 45).",
        )
        parser.add_argument(
            "--posts-count",
            type=int,
            default=18,
            help="Total Posts to create (plan default 18).",
        )
        parser.add_argument(
            "--announcements-count",
            type=int,
            default=5,
            help="Total Announcements to create (plan default 5).",
        )
        parser.add_argument(
            "--passes-count",
            type=int,
            default=22,
            help="Total VehiclePasses to create (plan default 22).",
        )

    # ────────────────────────── main entrypoint ──────────────────────────

    def handle(self, *args, **opts) -> None:
        reset = opts["reset"]
        dry_run = opts["dry_run"]
        use_env_password = opts["passwords_from_env"]

        # ── Resolve password ────────────────────────────────────────────
        password = self._resolve_password(use_env_password)

        # ── Seed global determinism (plan §11) ──────────────────────────
        init_random()  # seeds random + Faker

        # ── Reset phase ────────────────────────────────────────────────
        if reset:
            report = reset_scope.reset_demo_scope(dry_run=dry_run)
            self._log_reset_report(report, dry_run=dry_run)
            if dry_run:
                # Plan §10.1: dry-run MUST NOT seed; it exists to let
                # operators eyeball the scope before trusting a live run.
                self.stdout.write(self.style.WARNING(
                    "[dry-run] stopping before seed — no rows created.",
                ))
                return
        elif dry_run:
            # --dry-run without --reset is nonsense; surface the mistake.
            raise CommandError(
                "--dry-run only applies when --reset is also passed. "
                "Remove --dry-run to seed, or add --reset to audit.",
            )

        # ── Seed phase ─────────────────────────────────────────────────
        self.stdout.write(self.style.NOTICE("🌱 seed_demo: starting seed phase"))

        building_result = seed_building.seed()
        self.stdout.write(
            f"  • building={building_result.building.name!r} "
            f"entrances={len(building_result.entrances)} "
            f"units={len(building_result.units_by_key)} "
            f"(+{building_result.created_units} new)"
        )

        users_result = seed_users.seed(
            building_result=building_result,
            residents_count=opts["residents_count"],
            password=password,
        )
        total_users = (
            len(users_result.dispatchers) + len(users_result.guards)
            + len(users_result.workers) + len(users_result.residents)
            + len(users_result.unbound_residents)
            + (1 if users_result.tenant else 0)
        )
        self.stdout.write(
            f"  • users: total={total_users} "
            f"(dispatchers={len(users_result.dispatchers)}, "
            f"guards={len(users_result.guards)}, "
            f"workers={len(users_result.workers)}, "
            f"residents={len(users_result.residents)}, "
            f"unbound={len(users_result.unbound_residents)})"
        )

        issues_result = seed_issues.seed(
            users_result=users_result,
            building_result=building_result,
            count=opts["issues_count"],
        )
        self.stdout.write(
            f"  • issues: +{issues_result.created_issues} "
            f"(status={issues_result.status_counts()}, "
            f"overdue={issues_result.overdue}, "
            f"high={issues_result.high_priority}, "
            f"assigned={issues_result.assigned})"
        )

        posts_result = seed_posts.seed(
            users_result=users_result,
            building_result=building_result,
            posts_count=opts["posts_count"],
            announcements_count=opts["announcements_count"],
        )
        self.stdout.write(
            f"  • posts: +{posts_result.posts_created} "
            f"(skip={posts_result.posts_skipped}, replies=+{posts_result.replies_created}); "
            f"announcements: +{posts_result.announcements_created} "
            f"(skip={posts_result.announcements_skipped})"
        )

        passes_result = seed_passes.seed(
            users_result=users_result,
            count=opts["passes_count"],
        )
        self.stdout.write(
            f"  • passes: +{passes_result.created} "
            f"(pending={passes_result.pending}, closed={passes_result.closed})"
        )

        ratings_result = seed_ratings.seed(users_result=users_result)
        self.stdout.write(
            f"  • ratings: +{ratings_result.created} "
            f"(by occupation: {ratings_result.by_occupation})"
        )

        self.stdout.write(self.style.SUCCESS("✅ seed_demo: complete"))

    # ────────────────────────── helpers ──────────────────────────────

    def _resolve_password(self, use_env: bool) -> str:
        """Pick the password according to the ``--passwords-from-env`` flag.

        Fails loud when the operator asked for env sourcing but the
        variable isn't set — the last thing we want in prod is a silent
        fall-back to ``Demo1234!``.
        """
        if not use_env:
            return DEFAULT_DEMO_PASSWORD
        pw = os.environ.get("DEMO_PASSWORD")
        if not pw:
            raise CommandError(
                "--passwords-from-env was set but DEMO_PASSWORD env var "
                "is empty.  Populate the secret or drop the flag.",
            )
        if len(pw) < 8:
            # We enforce a floor because the default dev password is 9 chars
            # and we don't want a weaker prod password than the dev one.
            raise CommandError(
                "DEMO_PASSWORD must be ≥ 8 characters.",
            )
        return pw

    def _log_reset_report(self, report, *, dry_run: bool) -> None:
        style = self.style.WARNING if dry_run else self.style.NOTICE
        label = "dry-run" if dry_run else "reset"
        self.stdout.write(style(
            f"🧹 seed_demo [{label}] scope report: {asdict(report)}",
        ))
        if not dry_run and report.orphan_tags_removed:
            self.stdout.write(style(
                f"🧹 orphan tags removed: {report.orphan_tags_removed}",
            ))

    # ────────────────────────── sanity post-check ────────────────────

    # Reserved hook: kept as a placeholder for a future integration
    # assertion (plan §14) that queries the DB after seed to verify plan
    # numbers (count>=40 issues, ≥3 overdue, etc.).  Leaving unimplemented
    # in this file to avoid duplicating ``test_seed_demo.py`` coverage.
    def _sanity_check(self) -> None:  # pragma: no cover
        pass


# Defensive: if someone runs this file directly, give a clear error.
if __name__ == "__main__":  # pragma: no cover
    sys.stderr.write(
        "seed_demo is a Django management command — run it via "
        "`python manage.py seed_demo`.\n",
    )
    sys.exit(2)
