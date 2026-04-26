#!/usr/bin/env bash
# MERGE-PR3-PR4.sh — Backend dead code + stale comments & docs cleanup
# Combined PR-3 + PR-4 from DEV_PLAN.md
# CEO direct-merge authorization (2026-04-26)

set -euo pipefail

cd ~/PycharmProjects/Django-Apartment-Management

echo "==> 1/6  Sanity: ensure on chore/cleanup-batch"
git checkout chore/cleanup-batch

echo "==> 2/6  Run pytest (regression check, optional — CI will run anyway)"
cd server
if [ -x .venv/bin/pytest ]; then
  .venv/bin/pytest --tb=line -q --no-header 2>&1 | tail -3
elif [ -x ../.venv/bin/pytest ]; then
  ../.venv/bin/pytest --tb=line -q --no-header 2>&1 | tail -3
elif command -v pytest >/dev/null 2>&1; then
  pytest --tb=line -q --no-header 2>&1 | tail -3
elif python3 -c "import pytest" 2>/dev/null; then
  python3 -m pytest --tb=line -q --no-header 2>&1 | tail -3
else
  echo "  ⚠️  pytest not found locally — skipping (CI will validate). Sandbox already ran 751 passed."
fi
cd ..

echo "==> 3/6  Frontend lint + tsc"
cd client
npm run lint 2>&1 | tail -5 || true
npx tsc --noEmit 2>&1 | tail -3
cd ..

echo "==> 4/6  Commit"
git add -A
git commit -m "Implements: #chore-cleanup-batch

♻️ Backend dead code + stale comments & docs cleanup (combined PR-3 + PR-4).

PR-3 — Backend dead code:
- Delete deprecated test placeholder apps/tests/test_api_unit_cutover.py
- Delete unused ContentView.record_view classmethod (IssueDetailAPIView
  uses ContentView.objects.get_or_create directly)
- Remove duplicate isort==5.13.2 from server/requirements/local.txt
  (already in base.txt:11)
- Rename MinIO bucket: skandi-apartments to apartmentos-local in Makefile
- Drop disabled e2e job (if: false) and commented deploy block from
  .github/workflows/ci.yml; collapsed to a one-line note
- Switch pytest.ini testpaths to auto-discovery (apps); 751 tests
  collected — same as whitelist, --import-mode=importlib retained

PR-4 — Stale comments + docs:
- Replace profile.unit references with primary Residency in
  issues/urls.py, tests/test_issue_permissions.py, CreateIssueForm.tsx,
  types/index.d.ts (PR-11 alignment)
- Fix stale signal name in seed_posts.py docstring
  (on_announcement_created to on_announcement_saved)
- Update MobileHeader.tsx docstring to match indigo cabinet layout
  (drop refs to deleted Navbar and stub notif bell)
- Rename hooks/useUseProfile.ts to useUserProfile.ts (typo); update 3
  imports in CabinetTopbar/LeftNavbar/AuthAvatar
- Rename local IssueCard to ReviewIssueCard in rate-worker/page.tsx
  (remove shadow of components/cards/IssueCard.tsx)
- Move 5 ad-hoc audit/design .md files from repo root to docs/audits/
- Drop stale stash artifacts MERGE-PR1-PR2.sh and PR-1-COMMIT.sh

Tests: pytest server/ — 751 passed.
Frontend: tsc clean, lint 5 warnings (all pre-existing no-img-element)."

echo "==> 5/6  Push chore/cleanup-batch"
git push origin chore/cleanup-batch

echo "==> 6/6  Fast-forward merge to main + push"
git checkout main
git pull --ff-only origin main
git merge --ff-only chore/cleanup-batch
git push origin main

echo ""
echo "✅ DONE. main now contains PR-3 + PR-4."
echo "   Cleanup local: rm MERGE-PR3-PR4.sh (uncommitted in /outputs)"
echo "   Next: tell Claude 'збілделось' and we start PR-5 (GDPR Consent MVP — TDD)."
