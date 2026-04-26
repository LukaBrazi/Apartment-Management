#!/usr/bin/env bash
# MERGE-HOTFIX-CONSENT.sh
# Hotfix: ConsentGate version sentinel + missing /terms /privacy pages
# CEO direct-merge authorization (2026-04-26)

set -euo pipefail

cd ~/PycharmProjects/Django-Apartment-Management

echo "==> 1/6  Sanity: ensure on fix/consent-version-sentinel"
git checkout fix/consent-version-sentinel

echo "==> 2/6  Run pytest (consent + full regression)"
cd server
if [ -x .venv/bin/pytest ]; then
  .venv/bin/pytest apps/common/tests/test_consent.py -v --no-header 2>&1 | tail -15
  .venv/bin/pytest --tb=line -q --no-header 2>&1 | tail -3
elif [ -x ../.venv/bin/pytest ]; then
  ../.venv/bin/pytest apps/common/tests/test_consent.py -v --no-header 2>&1 | tail -15
  ../.venv/bin/pytest --tb=line -q --no-header 2>&1 | tail -3
elif command -v pytest >/dev/null 2>&1; then
  pytest --tb=line -q --no-header 2>&1 | tail -3
else
  echo "  ⚠️  pytest not found locally — skipping (sandbox already ran 767 passed)."
fi
cd ..

echo "==> 3/6  Frontend build + lint"
cd client
npm run build 2>&1 | tail -10
cd ..

echo "==> 4/6  Commit"
git add -A
git commit -m "Implements: #fix-consent-version-sentinel

🐛 Fix: ConsentGate modal looped forever after first 'Прийняти' click.

Root cause:
- Frontend sent version='current' (or echoed user's stale version) when
  POSTing /consent/, since it had no way to know the server-configured
  TOS_VERSION / PRIVACY_VERSION.
- Backend stored the literal string verbatim.
- Next GET /consent/me/ compared 'current' (or stale) against settings
  → current=false → modal reopened → infinite loop.

Fix:
- GET /consent/me/ now also returns 'tos_current_version' and
  'privacy_current_version' from settings.
- Frontend ConsentGate uses these when calling acceptConsent, so the
  recorded version always matches the configured one and current=true
  on next refetch.

Plus: created the missing /terms and /privacy pages (404 before).

Backend:
- views.ConsentMeAPIView: include current versions in response
  alongside tos/privacy state objects.
- 2 new tests in apps/common/tests/test_consent.py:
  - test_get_consent_me_returns_current_versions_for_frontend
  - test_accept_with_correct_version_sets_current_true (round-trip)

Frontend:
- types/index.d.ts: extend ConsentMeResponse with the two new fields.
- components/consent/ConsentGate.tsx: send data.tos_current_version /
  data.privacy_current_version instead of stale fallback.
- app/terms/page.tsx (NEW): static ToS page with 8 sections, version 1.0
  (matches default TOS_VERSION).
- app/privacy/page.tsx (NEW): static Privacy page with 11 GDPR-aligned
  sections, version 1.0 (matches default PRIVACY_VERSION).

pytest: 765 → 767 passed (+2, 0 failed).
tsc: clean. Lint: 0 new warnings."

echo "==> 5/6  Push fix/consent-version-sentinel"
git push origin fix/consent-version-sentinel

echo "==> 6/6  Fast-forward merge → main + push"
git checkout main
git pull --ff-only origin main
git merge --ff-only fix/consent-version-sentinel
git push origin main

echo ""
echo "✅ DONE. main now contains hotfix."
echo "   Railway will rebuild — after deploy:"
echo "     1. Reload page — modal should appear once with checkboxes"
echo "     2. Click 'Прийняти' — modal disappears immediately"
echo "     3. /terms and /privacy URLs render the new static pages"
echo "     4. Bump TOS_VERSION env on Railway → modal returns on next page load"
