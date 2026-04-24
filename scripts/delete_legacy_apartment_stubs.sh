#!/usr/bin/env bash
#
# delete_legacy_apartment_stubs.sh
#
# Removes every stub file left behind during the PR-4 → PR-7 series of
# the ``refactor/remove-legacy-apartment`` branch.
#
# Why the stubs exist at all: the session sandbox in which the refactor
# was executed can ``mv`` files (rewrite contents) but can't ``unlink``
# them.  Each file listed below was therefore emptied in place — reduced
# to a short module docstring explaining its obsolescence — and the real
# deletion was deferred to this script, which must run in a non-sandboxed
# checkout (your laptop, a CI job, etc.).
#
# Usage:
#   cd <repo-root>
#   git checkout refactor/remove-legacy-apartment
#   bash scripts/delete_legacy_apartment_stubs.sh
#   git add -A && git commit -m "chore(refactor): remove stubbed files from PR-4..PR-7"
#
# The script uses ``git rm`` so the removals land staged and the working
# tree and index stay in sync.  Missing files are tolerated (idempotent).

set -euo pipefail

# Resolve repo root — works whether you run the script from the repo
# root or from inside ``scripts/``.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# --- Backend stubs (PR-6 & PR-7) ---------------------------------------------
STUBS=(
  # PR-6: /apartments/* endpoints removed, the MyApartment view is gone.
  "server/apps/tests/test_my_apartment.py"

  # PR-7: Apartment model deleted; these tests exercised code paths that
  # no longer exist at runtime.
  "server/apps/tests/test_audit_legacy_apartments.py"
  "server/apps/tests/test_data_migration.py"
  "server/apps/tests/test_issue_unit_dual_read.py"
  "server/apps/tests/test_backfill_units_migration.py"

  # PR-7: audit_legacy_apartments is a no-op stub preserving argparse
  # flags for any automation still invoking it.  Delete it if and only
  # if nothing on the ops side still calls ``manage.py
  # audit_legacy_apartments``.  Comment this line out if you're not sure.
  "server/apps/common/management/commands/audit_legacy_apartments.py"

  # --- Frontend stubs (PR-4) -------------------------------------------------
  # The legacy tenant-apartment page, its create form, and its Yup
  # schema were emptied in PR-4 when the frontend cut over to Unit.
  "client/src/app/(estate)/apartment/page.tsx"
  "client/src/components/forms/apartment/ApartmentCreateForm.tsx"
  "client/src/lib/validationSchemas/ApartmentCreateSchema.ts"
)

echo "→ Removing ${#STUBS[@]} stub files under $REPO_ROOT"
echo

removed=0
skipped=0
for path in "${STUBS[@]}"; do
  if [[ -e "$path" ]]; then
    git rm -f -- "$path"
    removed=$((removed + 1))
  else
    echo "  skip (missing): $path"
    skipped=$((skipped + 1))
  fi
done

echo
echo "✓ Done.  Removed: $removed  Skipped: $skipped"
echo
echo "Next steps:"
echo "  git status"
echo "  git commit -m 'chore(refactor): remove stubbed files from PR-4..PR-7'"
