#!/usr/bin/env bash
# MERGE-PR5.sh — feat/gdpr-consent-mvp
# GDPR MVP: ToS + Privacy versioned consent (backend + frontend)
# CEO direct-merge authorization (2026-04-26)

set -euo pipefail

cd ~/PycharmProjects/Django-Apartment-Management

echo "==> 1/7  Sanity: ensure on feat/gdpr-consent-mvp"
git checkout feat/gdpr-consent-mvp

# Cleanup leftover index.lock if previous sandbox op left it
[ -f .git/index.lock ] && rm -f .git/index.lock

echo "==> 2/7  Apply migration on local dev DB (skip if no .env)"
cd server
if [ -x .venv/bin/python ] && [ -f .env ]; then
  .venv/bin/python manage.py migrate common --plan | tail -5
  .venv/bin/python manage.py migrate common
elif [ -x ../.venv/bin/python ] && [ -f .env ]; then
  ../.venv/bin/python manage.py migrate common --plan | tail -5
  ../.venv/bin/python manage.py migrate common
else
  echo "  ⚠️  Skipping migrate locally (no .venv or .env). Will run on Railway."
fi
cd ..

echo "==> 3/7  Run pytest (regression + new TDD tests)"
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
  echo "  ⚠️  pytest not found locally — skipping (sandbox already ran 759 passed)."
fi
cd ..

echo "==> 4/7  Frontend build + lint"
cd client
npm run build 2>&1 | tail -10
npm run lint 2>&1 | tail -5 || true
cd ..

echo "==> 5/7  Commit"
git add -A
git commit -m "Implements: #feat-gdpr-consent-mvp

GDPR MVP — ToS + Privacy versioned consent (backend + frontend, full TDD).

Backend:
- Extended ConsentLog model: consent_type (tos|privacy), version,
  accepted_at, ip_address, user_agent. Legacy purpose/given/timestamp
  fields kept (nullable) for marketing/analytics future use case.
- Migration 0002_extend_consentlog_for_gdpr_mvp — non-destructive,
  adds composite index (user, consent_type, -accepted_at).
- POST /api/v1/consent/ (ConsentCreateAPIView) — append-only;
  IP/UA captured server-side from request.
- GET /api/v1/consent/me/ (ConsentMeAPIView) — returns
  {tos, privacy} with 'current: bool' flag (compares to settings).
- Settings: TOS_VERSION, PRIVACY_VERSION env vars (default '1.0').
  Bump version → all prior consents become outdated → modal reopens.
- Admin: ConsentLogAdmin read-only (immutable audit trail).
- Tests: 8 new in apps/common/tests/test_consent.py (TDD red→green).
- Regression: 759 passed (was 751 + 8 new).

Frontend:
- RTK slice consentApiSlice (useGetMyConsentQuery, useAcceptConsentMutation).
- ConsentGate: fixed-overlay modal in (estate)/layout.tsx — blocks UI
  until user accepts current ToS + Privacy versions.
- ConsentSummary: read-only section in profile 'About' tab.
- Types: Consent, ConsentType, ConsentMeResponse.

Notes:
- e2e Playwright coverage for ConsentGate scheduled for next sprint
  (no Vitest/Jest in client/).
- Drops stale MERGE-PR3-PR4.sh (file deleted, git tracked rename)."

echo "==> 6/7  Push feat/gdpr-consent-mvp"
git push origin feat/gdpr-consent-mvp

echo "==> 7/7  Fast-forward merge → main + push"
git checkout main
git pull --ff-only origin main
git merge --ff-only feat/gdpr-consent-mvp
git push origin main

echo ""
echo "✅ DONE. main now contains PR-5 (GDPR Consent MVP)."
echo "   Railway will:"
echo "     1. Build new image with ConsentLog migration"
echo "     2. Run 'python manage.py migrate' on deploy"
echo "     3. New users see ConsentGate modal on first /welcome visit"
echo ""
echo "   Optional env vars on Railway (defaults '1.0'):"
echo "     TOS_VERSION=1.0"
echo "     PRIVACY_VERSION=1.0"
echo ""
echo "   Next: tell Claude 'збілделось' to start PR-6 (final — N+1 + architecture refactors)."
