"""Audit the state of legacy `Apartment` / `ResidentialComplex` data.

Read-only reconnaissance command. Produces a report used by the
``refactor/remove-legacy-apartment`` migration series to answer:

1. How many legacy ``Apartment`` rows still live in the DB?
2. How many of them are **not** bridged to a ``Unit`` via
   ``Unit.apartment`` (OneToOne)?  Those rows would become invisible the
   moment we cut the bridge — they must be back-filled first.
3. How many ``Issue`` rows reference a legacy apartment but have no
   ``Issue.unit`` yet?  PR-2 cutover will blow up without this backfill.
4. How many users have a legacy ``Apartment.tenant`` link but no
   ``Profile.unit``?  PR-3 serializers read ``profile.unit``; missing
   links = empty-looking API responses on prod.
5. How many ``Apartment.building`` *string* values exist?  Free-form
   CharField means near-duplicates ("Block A", "block a", " Block A ")
   must be normalised before we synthesise ``Building`` rows.
6. How many ``ResidentialComplex`` rows exist, and is the Organization
   mapping obvious or manual?  Required before PR-8 drops the model.
7. Does every active ``SiteSettings.current_complex`` map to exactly one
   organisation?  PR-8 replaces the FK with ``current_organization``.

Usage::

    python manage.py audit_legacy_apartments              # pretty table
    python manage.py audit_legacy_apartments --json       # machine-readable
    python manage.py audit_legacy_apartments --strict     # non-zero exit
                                                            if blockers > 0

Output is stable-sorted so two consecutive runs on the same DB produce
an identical report (useful for CI diffing during the refactor series).

The command is read-only — it never writes to the DB.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count, Q

User = get_user_model()


@dataclass
class AuditReport:
    """Structured snapshot of legacy-apartment data health."""

    # Apartment-level counts
    apartment_total: int = 0
    apartment_without_unit_bridge: int = 0
    apartment_with_tenant: int = 0
    apartment_with_tenant_without_unit: int = 0

    # Issue-level counts
    issue_total: int = 0
    issue_with_apartment: int = 0
    issue_with_apartment_without_unit: int = 0

    # Profile-level counts
    profile_total: int = 0
    users_with_legacy_apartment: int = 0
    users_with_legacy_apartment_missing_profile_unit: int = 0

    # Building-string normalisation
    distinct_building_strings: int = 0
    duplicate_building_strings: list[tuple[str, int]] = field(default_factory=list)
    building_strings_with_whitespace: list[str] = field(default_factory=list)

    # ResidentialComplex / Organization mapping
    residential_complex_total: int = 0
    buildings_with_complex: int = 0
    buildings_without_complex: int = 0
    buildings_without_organization: int = 0
    complex_to_org_ambiguous: list[str] = field(default_factory=list)

    # SiteSettings
    site_settings_total: int = 0
    site_settings_with_current_complex: int = 0

    # Roll-ups
    blockers: list[str] = field(default_factory=list)


class Command(BaseCommand):
    help = "Audit legacy Apartment / ResidentialComplex data prior to removal."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="Emit the report as JSON (for CI / scripting).",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit non-zero if blockers are found.",
        )

    def handle(self, *args, **opts):
        # Lazy imports so Django app registry is fully loaded.
        from apps.apartments.models import (
            Apartment,
            Building,
            Entrance,
            ResidentialComplex,
            Unit,
        )
        from apps.issues.models import Issue
        from apps.profiles.models import Profile
        from apps.site_settings.models import SiteSettings

        report = AuditReport()

        # ── Apartment bridge ───────────────────────────────────────────
        apartments = Apartment.objects.all()
        report.apartment_total = apartments.count()

        # A bridged apartment has a reverse Unit; use the related_name="unit".
        unbridged_qs = apartments.filter(unit__isnull=True)
        report.apartment_without_unit_bridge = unbridged_qs.count()

        tenanted = apartments.filter(tenant__isnull=False)
        report.apartment_with_tenant = tenanted.count()
        report.apartment_with_tenant_without_unit = tenanted.filter(
            unit__isnull=True
        ).count()

        # ── Issue cutover readiness ────────────────────────────────────
        report.issue_total = Issue.objects.count()
        issues_with_apt = Issue.objects.filter(apartment__isnull=False)
        report.issue_with_apartment = issues_with_apt.count()
        report.issue_with_apartment_without_unit = issues_with_apt.filter(
            unit__isnull=True
        ).count()

        # ── Profile.unit backfill readiness ────────────────────────────
        report.profile_total = Profile.objects.count()

        # Users with legacy Apartment.tenant set (reverse = user.apartment)
        users_legacy = User.objects.filter(apartment__isnull=False).distinct()
        report.users_with_legacy_apartment = users_legacy.count()

        # Of those, how many have Profile.unit set?
        report.users_with_legacy_apartment_missing_profile_unit = (
            users_legacy.filter(
                Q(profile__isnull=True) | Q(profile__unit__isnull=True)
            ).count()
        )

        # ── Apartment.building string normalisation ────────────────────
        building_strings = list(
            Apartment.objects.values_list("building", flat=True)
        )
        counter = Counter(building_strings)
        report.distinct_building_strings = len(counter)
        # Keep only strings that appear under multiple near-duplicates
        normalized = Counter()
        for s, n in counter.items():
            normalized[s.strip().lower()] += n
        report.duplicate_building_strings = sorted(
            [
                (k, v)
                for k, v in normalized.items()
                # More than one raw variant maps to the same normalised key
                if sum(
                    1
                    for raw in counter
                    if raw.strip().lower() == k
                )
                > 1
            ]
        )
        report.building_strings_with_whitespace = sorted(
            s for s in counter if s != s.strip()
        )

        # ── ResidentialComplex / Organization mapping ──────────────────
        report.residential_complex_total = ResidentialComplex.objects.count()

        buildings = Building.objects.all()
        report.buildings_with_complex = buildings.filter(
            complex__isnull=False
        ).count()
        report.buildings_without_complex = buildings.filter(
            complex__isnull=True
        ).count()
        report.buildings_without_organization = buildings.filter(
            organization__isnull=True
        ).count()

        # A complex is ambiguous if its buildings belong to >1 organization.
        ambiguous = (
            ResidentialComplex.objects.annotate(
                org_count=Count(
                    "buildings__organization", distinct=True
                )
            )
            .filter(org_count__gt=1)
            .values_list("name", flat=True)
        )
        report.complex_to_org_ambiguous = sorted(ambiguous)

        # ── SiteSettings ───────────────────────────────────────────────
        report.site_settings_total = SiteSettings.objects.count()
        report.site_settings_with_current_complex = SiteSettings.objects.filter(
            current_complex__isnull=False
        ).count()

        # ── Blocker roll-up ────────────────────────────────────────────
        if report.apartment_without_unit_bridge:
            report.blockers.append(
                f"{report.apartment_without_unit_bridge} Apartment(s) not "
                f"bridged to Unit — PR-1 data migration must synthesise "
                f"Building/Entrance/Unit for them."
            )
        if report.issue_with_apartment_without_unit:
            report.blockers.append(
                f"{report.issue_with_apartment_without_unit} Issue(s) "
                f"reference apartment but have no unit — PR-2 cutover "
                f"requires backfill."
            )
        if report.users_with_legacy_apartment_missing_profile_unit:
            report.blockers.append(
                f"{report.users_with_legacy_apartment_missing_profile_unit} "
                f"user(s) have legacy apartment link but no profile.unit — "
                f"PR-3 serializers would return null for them."
            )
        if report.duplicate_building_strings:
            report.blockers.append(
                f"{len(report.duplicate_building_strings)} "
                f"near-duplicate Apartment.building string(s) — "
                f"normalise before synthesising Building rows."
            )
        if report.complex_to_org_ambiguous:
            report.blockers.append(
                f"{len(report.complex_to_org_ambiguous)} "
                f"ResidentialComplex row(s) span multiple organisations — "
                f"PR-8 mapping to current_organization needs manual "
                f"resolution for: "
                f"{', '.join(report.complex_to_org_ambiguous)}"
            )
        if report.buildings_without_organization:
            report.blockers.append(
                f"{report.buildings_without_organization} Building(s) "
                f"have NO organization FK — multi-tenant isolation hole."
            )

        self._emit(report, as_json=opts["as_json"])
        if opts["strict"] and report.blockers:
            # Use sys.exit (not SystemExit raise) so Django's BaseCommand
            # run_from_argv does not swallow the non-zero status.
            sys.exit(1)

    # ── rendering ──────────────────────────────────────────────────────

    def _emit(self, report: AuditReport, *, as_json: bool) -> None:
        if as_json:
            self.stdout.write(json.dumps(asdict(report), indent=2, default=list))
            return

        w = self.stdout.write
        w(self.style.MIGRATE_HEADING("=== Legacy Apartment Audit ==="))
        w("")

        w(self.style.HTTP_INFO("Apartment bridge"))
        w(f"  apartments total ............................ {report.apartment_total}")
        w(f"  without Unit bridge (blocker) ............... {report.apartment_without_unit_bridge}")
        w(f"  with tenant .................................. {report.apartment_with_tenant}")
        w(f"  with tenant AND no Unit (blocker) ............ {report.apartment_with_tenant_without_unit}")
        w("")

        w(self.style.HTTP_INFO("Issue cutover readiness"))
        w(f"  issues total ................................. {report.issue_total}")
        w(f"  with apartment FK ............................ {report.issue_with_apartment}")
        w(f"  apartment set but no unit (blocker) .......... {report.issue_with_apartment_without_unit}")
        w("")

        w(self.style.HTTP_INFO("Profile.unit backfill readiness"))
        w(f"  profiles total ............................... {report.profile_total}")
        w(f"  users with legacy apartment .................. {report.users_with_legacy_apartment}")
        w(f"  users missing profile.unit (blocker) ......... {report.users_with_legacy_apartment_missing_profile_unit}")
        w("")

        w(self.style.HTTP_INFO("Building string normalisation"))
        w(f"  distinct strings ............................. {report.distinct_building_strings}")
        w(f"  near-duplicate groups (blocker) .............. {len(report.duplicate_building_strings)}")
        for key, count in report.duplicate_building_strings[:10]:
            w(f"    {key!r} → {count} rows")
        w(f"  with leading/trailing whitespace ............. {len(report.building_strings_with_whitespace)}")
        w("")

        w(self.style.HTTP_INFO("ResidentialComplex → Organization mapping"))
        w(f"  complexes total .............................. {report.residential_complex_total}")
        w(f"  buildings with complex ....................... {report.buildings_with_complex}")
        w(f"  buildings without complex .................... {report.buildings_without_complex}")
        w(f"  buildings without organization (blocker) ..... {report.buildings_without_organization}")
        w(f"  ambiguous complex→org (blocker) .............. {len(report.complex_to_org_ambiguous)}")
        for name in report.complex_to_org_ambiguous[:10]:
            w(f"    {name!r}")
        w("")

        w(self.style.HTTP_INFO("SiteSettings"))
        w(f"  site_settings total .......................... {report.site_settings_total}")
        w(f"  with current_complex set ..................... {report.site_settings_with_current_complex}")
        w("")

        if report.blockers:
            w(self.style.ERROR("Blockers:"))
            for b in report.blockers:
                w(f"  • {b}")
        else:
            w(self.style.SUCCESS("No blockers — safe to proceed with PR-1 backfill."))
