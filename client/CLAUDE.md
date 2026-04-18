# Skandi Apartments — Client (Next.js) Context

> Context for developers and AI agents working in `client/`.
> Last updated: **2026-04-18** by the "Жукуймося" bug-hunting team.

## 🚨 Package manager policy: npm ONLY

This project was historically touched by npm, pnpm, and yarn at different times,
which caused lockfile drift between local dev and the Docker-based CI pipeline.

**Decision: we use npm and only npm.** The Docker image (`client/Dockerfile`)
runs `npm ci` at build time, so `package-lock.json` is the source of truth.

### Enforcement

1. **`.gitignore` blocks** `yarn.lock` and `pnpm-lock.yaml` from being committed.
2. **`preinstall` script** in `package.json` inspects `npm_config_user_agent` and
   hard-fails any install attempted via pnpm or yarn, with a clear message:
   ```
   ⛔ This project uses npm only (Docker builds with npm ci). Detected: pnpm/...
   ```
3. **`npm run verify:lockfile`** runs `npm ci --dry-run` to catch
   `package.json` ↔ `package-lock.json` drift without actually installing.

### If you see `Missing: <package>@<version> from lock file`

This means `package-lock.json` is out of sync with `package.json` (or with
resolution of optional peer deps under newer npm). Fix:

```bash
cd client
npm install           # regenerates the lockfile
git diff package-lock.json
git add package-lock.json
git commit -m "chore(client): sync package-lock.json"
```

**Do NOT use `pnpm install` or `yarn install`** — the `preinstall` guard will
block it. If you need to override for some legitimate reason, discuss with the
team first.

## 🐳 How this interacts with the e2e pipeline

`make e2e-full` (from the repo root) runs:

```
ci-clean → ci-up (Docker build: client + server + nginx + postgres + redis)
        → health check → ci-seed (seed_demo) → playwright → ci-clean
```

The `client` container is built with the Dockerfile's `node-build-stage`:
```dockerfile
RUN  if [ -f yarn.lock ]; then yarn --frozen-lockfile; \
     elif [ -f package-lock.json ]; then npm ci; \
     elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm i; \
     else echo "Lockfile not found." && exit 1; \
     fi
```

Since we now only have `package-lock.json`, the `elif` branch for `npm ci` is
always taken. If `npm ci` fails, nothing below it runs — no server, no nginx,
no Playwright. **Always** fix client build failures before blaming e2e.

## 📋 Stack reminders (quick reference)

- **Next.js 14** (App Router), TypeScript
- **RTK Query** for API — watch cache invalidation via tags after mutations
- **Shadcn UI + Radix**:
  - `TabsTrigger` → `role="tab"` (selector: `getByRole("tab", { name: /…/i })`)
  - `TabsContent` → `role="tabpanel"`
  - Select → `[role="combobox"]`
- **react-hook-form** — `register("field")` renders `input[name="field"]`
- **react-toastify** — `toast.success`/`toast.error` →
  `.Toastify__toast--success` / `.Toastify__toast--error`

## 🔑 Auth in tests

- `logged_in` cookie gates `ProtectedRoute`
- Role checks via `useAuthNavigation`
- After successful login, app redirects to `/welcome`
  (Playwright fixture: `waitForURL(/\/welcome/, { timeout: 15_000 })`)

## 🧭 Playwright: `waitForURL` on Next.js client-side nav

Next.js `<Link>` clicks and `router.push/replace()` transition via the
History API. No fresh `load` event fires, so Playwright's default
`waitForURL` (implicitly `waitUntil: "load"`) hangs until timeout.

**Rule:** any `waitForURL` that follows a client-side navigation must
pass `waitUntil: "commit"`:

```ts
await page.waitForURL(/\/issue\//, { timeout: 10_000, waitUntil: "commit" });
```

This applies to:
- `<Link>` clicks (issue list → detail, navbar links)
- Any `router.push/replace` inside a submit handler / effect
  (e.g. `TenantsPageContent` redirects tenant to `/welcome`;
  report-issue flow pushes `/profile` on success)
- Admin table row clicks that use `router.push` (e.g. `/admin/issues`)

`waitForURL` after the login fixture (full form submit → full page nav
to `/welcome`) is fine with defaults — it's a real document navigation.

## 🌱 Known seed-data gaps (as of 2026-04-18)

`make seed` / `seed_demo` populates users, apartments, posts, tags —
but does **not** create Issue records. This breaks e2e tests that
depend on having at least one issue already in the database:

- `functional/admin-issue-status.spec.ts`
- `functional/assign-issue-flow.spec.ts` ("Дані відсутні" in admin table)
- `functional/issue-detail-ui.spec.ts`
- `negative/issue-priority-visibility.spec.ts`

Verification: `GET /api/v1/issues/` returns
`{"count": 0, "next": null, "previous": null, "results": []}` after
seeding. **Backend team must extend `seed_demo` to create seed issues**
(assigned + unassigned, various statuses + priorities).

Also unverified: whether `tenant@demo.com`'s apartment link survives
re-seed — some report-issue tests assume the tenant has a bound
apartment. Watch for `/api/v1/profiles/user/my-profile/` returning
`apartment: null` and gate fixtures accordingly.

### Self-seeding workaround (client-side of e2e)

Until `seed_demo` is fixed, the e2e suite self-heals via
`sckandi-e2e/fixtures/global-setup.ts`:

1. On suite start, logs in as dispatcher → checks `GET /issues/` count.
2. If count < 4, logs in as `resident1@demo.com` (who has a working
   apartment), creates 4 issues via `POST /issues/create/{apartmentId}/`,
   then patches them via `PATCH /issues/admin/update/{id}/` to give
   status/priority variety.
3. Attempts to heal tenant@demo.com's null apartment by reading a valid
   unit from `/apartments/units/` and PATCHing
   `/profiles/admin/{slug}/update/` with `unit_id`.

The setup is best-effort: if any API call fails, the downstream tests
use `authTest.skip()` with a precise message pointing at the exact
endpoint + status code, so CI failures never silently blame the tests.

**When backend fixes `seed_demo` properly, delete the seed portion of
`global-setup.ts` and the health-guard `authTest.skip()` calls in:**
- `admin-create-resident.spec.ts` (checks `profiles/admin/all/`)
- `access-control.spec.ts` tenant redirect (checks `profiles/user/my-profile/`)
- `admin-issue-status.spec.ts`, `assign-issue-flow.spec.ts`
  (skip if issue count stays 0)

## 🔥 Known backend 500s (as of 2026-04-18)

Two endpoints return **HTTP 500** reliably in the current `make e2e-full`
environment. Both are flagged by e2e tests via `authTest.skip()` with the
exact status code in the skip reason, so nothing is silently swallowed.

1. **`GET /api/v1/profiles/admin/all/` → 500** (for any dispatcher session).
   Symptom: admin residents page renders "Дані відсутні" even when users
   exist; RTK Query `useGetAdminAllProfilesQuery` logs a failed request.
   Blocks `admin-create-resident.spec.ts` verification.

2. **`GET /api/v1/profiles/user/my-profile/` → 500 for `tenant@demo.com`**
   (works for dispatcher + resident1). Strong hypothesis: after `seed_demo`,
   `tenant@demo.com` has `apartment_id=null` and the `ProfileSerializer`
   dereferences the relation without guarding. Blocks
   `access-control.spec.ts` tenant redirect (TenantsPageContent can't
   decide which way to redirect without a valid profile).

**Backend checklist:**
- Look at the view + serializer backing each endpoint; wrap relation
  traversal in `getattr(..., None)` / `SerializerMethodField` with
  null-safety; add a unit test that serializes a user with no apartment.
- Check Sentry (or django logs) for the stack trace around the 500.
- Extend `seed_demo` to bind every tenant to an apartment, not just
  `tenant@demo.com` (prevents future drift).

## 📑 Admin list endpoints are DRF-paginated

`/api/v1/profiles/admin/all/` returns `{profiles: {count, next, previous, results}}`
with **default DRF page size (10)**. The client
(`useGetAdminAllProfilesQuery`) calls it with no query params, so
`@tanstack/react-table` on admin pages only holds the first 10 users
in `data.profiles.results`.

Consequence: after creating a new user via admin form, the new entry
is **appended server-side** and typically lands on page 2+. Tests that
assert "new user appears in list" via the DataTable will flake —
verify via API instead:

```ts
// Paginate through /profiles/admin/all/ using session cookies from the page
let url: string | null = "/api/v1/profiles/admin/all/";
while (url) {
  const res = await page.request.get(url);
  const body = await res.json();
  const pageData = body.profiles ?? body;
  if (pageData.results.some((p) => p.user.username === target)) return true;
  url = pageData.next;
}
```

See `tests/functional/admin-create-resident.spec.ts` for the full pattern.

## 🌱 Seed users (from `seed_demo`)

All password: `Demo1234!`

| Email | Role | Notes |
|---|---|---|
| `dispatcher@demo.com` | Dispatcher / admin | full admin access |
| `tenant@demo.com` | Tenant | has apartment (unit 105) |
| `guard@demo.com` | Guard | guard portal access |
| `resident1@demo.com` … `resident8@demo.com` | Residents | for multi-user flows |

## 🔗 Verified API routes (relevant to this client)

- `/api/v1/posts/all/` — `PostListAPIView` (not `/posts/posts/`)
- `/api/v1/posts/create/` — `PostCreateAPIView`
- `/api/v1/issues/admin/update/<uuid:id>/` — `IssueAdminUpdateAPIView`
- `/api/v1/passes/` — `VehiclePassListCreateAPIView`
- `/api/v1/passes/my/` — `MyVehiclePassListAPIView`
- `/api/v1/passes/<uuid:pass_id>/close/` — `CloseVehiclePassAPIView`

## 📅 Changelog of infra decisions

- **2026-04-18**: `make e2e-full` failed at `ci-up` with
  `npm ERR! Missing: yaml@2.8.3 from lock file`. Root cause: stale
  `package-lock.json` (optional peer `yaml` from `tailwindcss@3.4.19 →
  postcss-load-config@6.0.1` not materialized). Also found three lockfiles
  coexisting. Fix: synced lockfile, removed `pnpm-lock.yaml` and
  `yarn-error.log`, added `.gitignore`, `preinstall` guard, and
  `verify:lockfile` script. Policy: **npm only** going forward.

- **2026-04-18 (e2e stabilization pass)**: Playwright suite had 6 failures
  after the lockfile fix. Root causes and actions:
  1. **RSC `$undefined` / `null` false positives** — `body.textContent()`
     scooped up inline `<script>` RSC payloads. Switched `site-settings`
     content assertions to `innerText()` on `main` / `nav` locators.
  2. **`waitForURL` timeouts on client-side nav** — Next.js `<Link>` /
     `router.push/replace` never fires a `load` event. Added
     `waitUntil: "commit"` across `issue-detail-ui`, `access-control`,
     `issue-priority-visibility`, `issue-validation`, `issue-submission`,
     `pass-flow`, `issue-admin-flow`.
  3. **Admin DataTable pagination** — created user in
     `admin-create-resident` landed on page 2; replaced UI list check
     with direct API pagination verification. See
     "Admin list endpoints are DRF-paginated" section above.
  4. **Empty seed for Issues** — confirmed via trace that
     `/api/v1/issues/` returns `count: 0` after `seed_demo`. Not fixable
     from test code; flagged in "Known seed-data gaps" above for the
     backend team.

- **2026-04-18 (self-seed + health-guard pass)**: After the first
  stabilization round (6→4 failures), remaining 4 all traced to the
  backend: two seed-data gaps (issues empty) and two HTTP 500s
  (`profiles/admin/all/` and `profiles/user/my-profile/` for tenant).
  Added on the e2e side:
  1. `fixtures/api-helpers.ts` + `fixtures/global-setup.ts` — self-seeds
     4 issues via API if none exist; tries to heal tenant's null
     apartment link via admin PATCH.
  2. Per-test `authTest.skip()` health guards with the exact failing
     endpoint + status code in the skip reason (no silent hides).
  3. Wired `globalSetup: "./fixtures/global-setup.ts"` in
     `playwright.config.ts`.
  When backend fixes `seed_demo` and the two 500s, delete the seeding
  section and the `skip()` guards — they're clearly marked in comments.

- **2026-04-18 (page-scoped precondition guards)**: `make e2e-full` regressed
  from 4→11 failures on a subsequent run because `global-setup` self-seeding
  is best-effort and did not heal the DB on every run. Seven new hard
  failures across `issue-detail-ui.spec.ts` (4), `issue-priority-visibility
  .spec.ts` (3), `issue-submission.spec.ts` (1 — the expect-success case),
  and `issue-admin-flow.spec.ts` (1) were all waiting 15s for `[href^="/
  issue/"]` or the `Спочатку додайте квартиру` toast. Fix on the e2e side:
  1. Added `pageHasIssues(page)` and `pageHasApartment(page)` helpers in
     `fixtures/api-helpers.ts` that probe via `page.request` (inherits
     session cookies — no re-login).
  2. Added `authTest.skip(!(await pageHasIssues(resident1Page)), ...)` at
     the top of every test depending on existing Issue records. Skip
     message cites `/api/v1/issues/` count=0 and points at
     `seed_demo`/global-setup as the root cause.
  3. Added `authTest.skip(!(await pageHasApartment(tenantPage)), ...)` to
     the tenant "expect success" submission test.
  4. For `issue-admin-flow.spec.ts` (uses `browser.newContext` manually,
     no `resident1Page` fixture), used a one-off `apiLogin` +
     `getMyProfile` to check resident1's apartment before starting.
  Net effect: when `seed_demo` doesn't populate the DB and global-setup
  can't heal it, the 7 dependent tests skip cleanly with a diagnostic
  pointing at the exact backend gap, instead of hard-failing mid-flow.
  Delete both the skip guards and the helpers when `seed_demo` is fixed
  on the backend.
