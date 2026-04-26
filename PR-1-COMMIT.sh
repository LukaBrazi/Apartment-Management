#!/usr/bin/env bash
# PR-1: Critical Security & Infra Fixes
# Run from Mac terminal (NOT from sandbox — .git/index.lock issue on macOS APFS)
#
# Prereq: clean main, no uncommitted work
# What this does: creates fix/critical-security branch, commits 18 file changes, opens PR

set -euo pipefail

cd ~/PycharmProjects/Django-Apartment-Management

# 1. Sanity: clean main
if [ -n "$(git status --porcelain | grep -v 'PR-1-COMMIT.sh')" ]; then
  echo "⚠️  Working tree NOT clean. The sandbox left these changes ready to commit:"
  git status --short
  echo ""
  echo "These changes ARE what we want to commit. Proceeding will create branch and commit them."
  read -p "Continue? [y/N] " -n 1 -r
  echo
  [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

# 2. Create feature branch from current state (changes already in working tree)
git checkout -b fix/critical-security 2>/dev/null || git checkout fix/critical-security

# 3. Explicit git mv for renames (so history follows)
# Logos: skandi-* → apartmentos-* (sandbox already moved files; tell git)
git rm -f client/public/assets/logos/skandi-logo-full.svg 2>/dev/null || true
git rm -f client/public/assets/logos/skandi-logo-full-dark.svg 2>/dev/null || true
git rm -f client/public/assets/logos/skandi-mark.svg 2>/dev/null || true
git rm -f EstateOS_Lead_Manager_Pack_UA.docx 2>/dev/null || true

# 4. Stage everything (including new lockfile, new test files, new permissions module)
git add client/package-lock.json
git add -A

# 5. Commit
git commit -m "Implements: #fix-critical-security

🔒 Critical security & infra fixes (PR-1).

RBAC permissions refactor (TDD):
- New apps/common/permissions.py with IsGuard, IsTenant, IsStaff,
  IsGuardOrAdmin (no silent except Exception: pass — only
  Profile.DoesNotExist with logger.warning).
- passes/permissions.py is now a thin re-export.
- issues/views.py uses shared IsStaffOrSuperUser instead of inline class.

JWT signing key fail-fast:
- Removed insecure 'test-signing-key-change-in-production' default
  from SIMPLE_JWT.SIGNING_KEY in base.py. simplejwt now defaults to
  settings.SECRET_KEY; production fails fast on missing
  DJANGO_SECRET_KEY env.

S3 storage backend:
- Renamed CustomS3Boto3Storage → LocalMinioS3Storage with explicit
  DEV-ONLY docstring (https→http downgrade for local MinIO without TLS).

Brand cleanup:
- Logos renamed skandi-* → apartmentos-*; updated MobileHeader.tsx,
  Navbar.tsx imports.
- Removed client/package-lock.json from .gitignore (npm-only policy).
- Removed EstateOS_Lead_Manager_Pack_UA.docx artifact.
- client/CLAUDE.md heading: 'Skandi Apartments' → 'ApartmentOS'.

Pytest infrastructure:
- pytest.ini: added apps/common/tests to testpaths and
  --import-mode=importlib (resolves 'tests' package name conflicts
  across multiple apps).

Pre-existing test fixes (exposed by importlib mode):
- apps/feedback/views.py: moved send_feedback_notification_task
  import to module level (was lazy inside perform_create — broke
  mock.patch).
- apps/issues/tests/test_reviewable_issues.py:54: Entrance
  entrance_number=1 → name='1' (model field is 'name').

Tests:
- 23 new tests (TDD red→green→refactor)
  • 20 in apps/common/tests/test_permissions.py
  • 3 in apps/tests/test_jwt_signing_key_required.py
- Full suite: 751 passed, 0 failed."

# 6. Push
git push -u origin fix/critical-security

# 7. Open PR
gh pr create --base main \
  --title "fix: critical security & infra (PR-1)" \
  --body "$(cat <<'EOF'
# PR-1 — Critical Security & Infra Fixes

First of 6 PRs from `DEV_PLAN.md` (tech-debt audit 2026-04-26).

## What & Why

### 🔒 RBAC permissions refactor (TDD)
Previously `passes/permissions.py` and `issues/views.py:IsStaffOrSuperUser` swallowed `except Exception: pass` when reading `user.profile`. **Silent failure** — any error (not just missing Profile) was hidden, masking race conditions and inconsistent DB state.

- New `apps/common/permissions.py` with `IsGuard`, `IsTenant`, `IsStaff`, `IsGuardOrAdmin`, `IsStaffOrSuperUser` (alias).
- Only `Profile.DoesNotExist` is caught, with `logger.warning("user %s has no profile")`.
- 20 unit tests cover all branches (TDD red→green).
- `passes/permissions.py` is now a thin re-export; `issues/views.py` imports from common.

### 🔑 JWT SIGNING_KEY fail-fast
`SIMPLE_JWT["SIGNING_KEY"]` had a default `"test-signing-key-change-in-production"`. On production with `DJANGO_SECRET_KEY` env missing, JWTs would be signed with a publicly known key — **forge token attack**.

- Removed `SIGNING_KEY` from `SIMPLE_JWT` dict — simplejwt defaults to `settings.SECRET_KEY`.
- `production.py` already has `SECRET_KEY = env("DJANGO_SECRET_KEY")` with no default — boot fails with `ImproperlyConfigured` if env missing.
- 3 regression tests in `apps/tests/test_jwt_signing_key_required.py`.

### ⚠️ S3 storage dev-only marker
`storage_backends.py:CustomS3Boto3Storage.url()` does `https→http` downgrade — intentional for local MinIO without TLS, but the class wasn't marked dev-only.

- Renamed `CustomS3Boto3Storage → LocalMinioS3Storage`.
- Added explicit "DEV-ONLY: do NOT use in staging/production" docstring.

### 🎨 Brand cleanup
- Logo rename: `skandi-logo-*.svg`, `skandi-mark.svg` → `apartmentos-*.svg` (+ updated imports in `MobileHeader.tsx`, `Navbar.tsx`).
- `client/CLAUDE.md:1` heading: "Skandi Apartments" → "ApartmentOS".
- Deleted `EstateOS_Lead_Manager_Pack_UA.docx` (legacy marketing pack).
- `.gitignore`: removed line 46 `client/package-lock.json` (npm-only policy → lockfile is source of truth).

### 🧪 Pre-existing test fixes
Adding `--import-mode=importlib` to `pytest.ini` (required to avoid `tests` package name conflicts across apps after creating `apps/common/tests/`) revealed 12 hidden failures:

1. **`apps/feedback/views.py`** — `send_feedback_notification_task` was imported lazily inside `perform_create()`. `mock.patch("apps.feedback.views.send_feedback_notification_task")` fails because the attribute isn't on the module. → Moved import to module level.
2. **`apps/issues/tests/test_reviewable_issues.py:54`** — `Entrance(entrance_number=1, ...)` but `Entrance` model field is `name` (str). → Fixed.

## How to Test

```bash
cd server
pytest apps/common/tests apps/tests/test_jwt_signing_key_required.py
# 23 passed
pytest  # full suite
# 751 passed, 0 failed
```

Manual:
1. Run dev server with `DJANGO_SECRET_KEY` env — JWT auth works.
2. Remove `DJANGO_SECRET_KEY` in production.py mode — Django won't start (fail-fast).

## Rollback

```bash
git revert <merge-sha>
```
All changes in one PR, safe to revert.

## Checklist

- [x] TDD red→green→refactor for new code
- [x] pytest green (751/751 passed, 0 failed)
- [x] No new dependencies
- [x] No DB migrations
- [x] Self-contained (logo rename + import update in same PR)
- [x] No secrets/credentials in code
- [x] Branch is feature branch (not main)
EOF
)"

echo ""
echo "✅ PR-1 created. Review in browser, merge when ready."
echo "   Then run: rm DEV_PLAN.md && git add -A && git commit -m 'chore: remove DEV_PLAN.md after PR-1 merge'"
echo "   (or keep DEV_PLAN.md for PR-2..PR-6 — Claude will tell you when to delete)"
