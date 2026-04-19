"""Legacy audit command — obsolete after PR-7.

The original command (see git history) inspected ``Apartment`` /
``Unit.apartment`` / ``Issue.apartment`` cohesion prior to the
PR-1…PR-3 cutover series.  Once PR-7 deleted the ``Apartment`` model
there is nothing left to audit; the command now no-ops with a notice.

Kept on disk (instead of deleted) because the sandbox that produced
PR-7 cannot unlink files.  The stub preserves the management-command
entry point so any automation that still calls it gracefully reports
"nothing to do".
"""
from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Obsolete after PR-7 — the legacy Apartment model is gone so there "
        "is no longer any pre-migration state to inspect."
    )

    def add_arguments(self, parser):
        # Preserve the original flags so callers that still pass
        # --json / --strict don't fail with 'unrecognised arguments'.
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--strict", action="store_true")

    def handle(self, *args, **opts):
        msg = (
            "audit_legacy_apartments: no-op (PR-7 removed the legacy "
            "Apartment model)."
        )
        if opts.get("as_json"):
            self.stdout.write('{"status": "obsolete", "blockers": []}')
        else:
            self.stdout.write(self.style.SUCCESS(msg))
