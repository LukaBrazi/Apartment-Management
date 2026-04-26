#!/usr/bin/env bash
# Merge PR-1 + PR-2 → main + push
# CEO explicit authorization (2026-04-26): direct merge to main, no PR review
#
# Run from Mac terminal in repo root.

set -euo pipefail

cd ~/PycharmProjects/Django-Apartment-Management

echo "==> 1/6  Sanity: ensure on chore/frontend-cleanup"
git checkout chore/frontend-cleanup

echo "==> 2/6  Regenerate package-lock.json (package.json changed)"
cd client
npm install
cd ..

echo "==> 3/6  Build check"
cd client
npm run build
cd ..

echo "==> 4/6  Commit PR-2 (also includes DEV_PLAN.md updates)"
git add -A
git commit -m "Implements: #chore/frontend-cleanup

Frontend dead-code removal — components, RTK hooks, Tailwind tokens.

Components removed (9):
- 4 obsolete navbar components (Navbar, RightNavbar, MobileNavbar,
  ThemeSwitcher) — replaced by cabinet redesign 2026-04-24
- AdminDashboard — superseded by app/admin/page.tsx
- TenantInfo card — 0 imports
- 3 unused Shadcn primitives (form, menubar, sheet)

Components kept:
- pagination + skeleton — actively used (audit was wrong)
- NotificationBell — kept as scaffold with @stub JSDoc, no longer rendered

RTK Query (7 hooks + endpoints):
- useGetUserQuery, useRefreshJWTMutation (refresh handled in baseApiSlice
  directly via fetchBaseQuery)
- useGetAllIssuesQuery
- useGetMyPostsQuery, useUnBookmarkPostMutation, useGetAllRepliesQuery
- useGetTelegramBotQuery

Type cleanup:
- Removed unused RepliesResponse interface

Tailwind config:
- Removed dead tokens: googleBlue, richBlack, ballonWhite,
  nordic.* (12 keys), fontFamily.openSans
- 0 references found in tsx/css

Dependencies:
- Removed @radix-ui/react-menubar (only used by deleted menubar.tsx)
- package-lock.json regenerated

Artifacts:
- Removed empty 'Select' file in repo root
- Removed unused next.svg, vercel.svg from client/public

Tests:
- npm run lint: 0 new warnings (5 pre-existing about <img>)
- tsc --noEmit: clean
- npm run build: success"

echo "==> 5/6  Push chore/frontend-cleanup"
git push origin chore/frontend-cleanup

echo "==> 6/6  Fast-forward merge → main + push"
git checkout main
git pull --ff-only origin main
# Linear history: chore/frontend-cleanup branched from fix/critical-security tip,
# so merging it into main brings BOTH PR-1 and PR-2 commits in one fast-forward.
git merge --ff-only chore/frontend-cleanup
git push origin main

echo ""
echo "✅ DONE. main now contains PR-1 + PR-2."
echo "   Cleanup: rm MERGE-PR1-PR2.sh && git add -A && git commit -m 'chore: remove merge script' && git push"
echo "   Next: tell Claude 'білдиться' to start PR-3 (backend cleanup)."
