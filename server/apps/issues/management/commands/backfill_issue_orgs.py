"""Backfill ``Issue.organization`` for legacy rows where it is NULL.

PR-15 fixed the runtime fallback so tenants no longer see an empty
``/profile?tab=my-issues`` due to NULL-org rows.  This command cleans up
the underlying data so admin filters, org-scoped reports, and future
queries do not need to special-case NULL.

Resolution order per row:
1.  ``issue.unit.entrance.building.organization`` — strongest signal,
    matches what ``IssueCreateAPIView`` would pin today.
2.  ``issue.unit.organization`` (if entrance/building chain is broken).
3.  ``reported_by``'s first active ``OrganizationMembership``.

Rows that resolve no organization through any path are reported but
left untouched — those are dangling legacy rows we can deal with
manually.

Run it with ``python manage.py backfill_issue_orgs`` (use ``--dry-run``
to preview).
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.issues.models import Issue


def _resolve_org_for_issue(issue: Issue):
    """Return the org that ``issue`` should be pinned to, or None."""
    unit = getattr(issue, "unit", None)
    if unit is not None:
        entrance = getattr(unit, "entrance", None)
        if entrance is not None:
            building = getattr(entrance, "building", None)
            if building is not None and getattr(building, "organization_id", None):
                return building.organization
        # Entrance/building chain may be broken — try the unit directly.
        if getattr(unit, "organization_id", None):
            return unit.organization

    reporter = getattr(issue, "reported_by", None)
    if reporter is not None:
        from apps.organizations.utils import get_user_primary_organization

        return get_user_primary_organization(reporter)
    return None


class Command(BaseCommand):
    help = "Backfill Issue.organization for rows where it is NULL."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change without writing to the DB.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)

        candidates = (
            Issue.objects.filter(organization__isnull=True)
            .select_related(
                "unit__entrance__building__organization",
                "unit__organization",
                "reported_by",
            )
        )
        total = candidates.count()
        self.stdout.write(
            self.style.NOTICE(
                f"Найдено {total} Issue з organization=NULL"
                + (" (dry-run, нічого не змінюємо)" if dry_run else "")
            )
        )

        updated = 0
        unresolved = 0
        with transaction.atomic():
            for issue in candidates.iterator():
                org = _resolve_org_for_issue(issue)
                if org is None:
                    unresolved += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ↯ Issue {issue.id} ({issue.title[:50]}…) — "
                            "не вдалося resolve org, залишено NULL."
                        )
                    )
                    continue
                if dry_run:
                    self.stdout.write(
                        f"  → Issue {issue.id} → org='{org.name}' (slug={org.slug})"
                    )
                    updated += 1
                    continue
                issue.organization = org
                issue.save(update_fields=["organization"])
                updated += 1

            if dry_run:
                # Roll the transaction back even though we made no writes.
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Оновлено: {updated} (NULL після прогону: {unresolved})."
                + (" [dry-run]" if dry_run else "")
            )
        )
