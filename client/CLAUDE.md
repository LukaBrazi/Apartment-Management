# ApartmentOS — Client (Next.js) Context

> Context for developers and AI agents working in `client/`.
> Last updated: **2026-04-29 (evening)** — after PR-13a (billing core),
> i18n cleanup (Total → Всього on Reports tab), admin dashboard clickable
> rows, PR-14 (Buildings nested create + edit + visibility fix + Issue
> staff edit dialog).
>
> RTK Query tag types now include `"AdminBuildings"`, `"AdminEntrances"`,
> and (PR-15) `"AdminContacts"` (`baseApiSlice.ts`). Mutations on entrances
> invalidate `["AdminEntrances", "AdminBuildings", "Apartment"]` так що list
> buildings + units count + manage-entrances modal оновляться синхронно.
> Mutations on admin contacts invalidate `["AdminContacts", "SiteSettings"]`
> щоб публічна сторінка `/contacts` (читає `getSiteSettings`) бачила нові
> зміни одразу.

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

## 🌱 Seed data — the new `seed_demo`

Since **2026-04-18** `seed_demo` is a full, plan-spec-compliant dataset per
`client/docs/DEMO_SEED_PLAN.md`. Orchestrator lives at
`server/apps/common/management/commands/seed_demo.py`, module implementations
under `server/apps/common/seed/`. What you get after one `make seed`:

| Entity          | Count | Notes                                                      |
|-----------------|-------|------------------------------------------------------------|
| Building        | 1     | «Зелений Квартал — Демо»                                    |
| Entrances       | 3     | А, Б, В (В navigator-empty per plan §3)                    |
| Units           | 48    | Bound to entrances                                         |
| Users           | 45    | 2 dispatchers + 3 guards + 8 workers + 32 residents        |
| Issues          | 45    | Status + priority mix per plan §5                          |
| Posts           | 18    | 12 canonical tags + 27 replies + 5 announcements           |
| VehiclePasses   | 22    | 11 pending + 11 closed                                     |
| Ratings         | 35    | Per-occupation bias (plumber 4.8, painter 3.5)             |

Reset semantics: `python manage.py seed_demo --reset` scoped-deletes demo rows
(email `@demo.com` + building name «Зелений Квартал — Демо») then re-seeds.
Runs idempotently — a second `seed_demo` produces zero new rows. See the
backend `server/apps/common/seed/reset_scope.py` and
`apps/tests/test_reset_demo_scope.py` for the safety invariants.

## 🌱 Seed users (from `seed_demo`)

All password: `Demo1234!` (prod rotates via `DEMO_PASSWORD` env + `--passwords-from-env`).

| Email | Role | Notes |
|---|---|---|
| `dispatcher@demo.com`, `dispatcher2@demo.com` | Dispatcher / admin | full admin access |
| `guard@demo.com`, `guard2@demo.com`, `guard3@demo.com` | Guards | guard portal access |
| `plumber@demo.com`, `electrician@demo.com`, `carpenter@demo.com`, `mason@demo.com`, `roofer@demo.com`, `painter@demo.com`, `painter2@demo.com`, `hvac@demo.com` | Workers | each bucketed by occupation |
| `tenant@demo.com` | Tenant | has apartment bound to a demo unit |
| `resident1@demo.com` … `resident8@demo.com` + 21 more | Residents | for multi-user flows |

## 🔗 Verified API routes (relevant to this client)

- `/api/v1/posts/all/` — `PostListAPIView` (not `/posts/posts/`)
- `/api/v1/posts/create/` — `PostCreateAPIView` (throttle: `post_create` 10/h)
- `/api/v1/issues/admin/update/<uuid:id>/` — `IssueAdminUpdateAPIView`
- `/api/v1/issues/<uuid:id>/review/` — `IssueReviewAPIView` (POST: submit review, GET: list reviews)
- `/api/v1/issues/` (POST) — `IssueCreateAPIView` (throttle: `issue_create` 20/h)
- `/api/v1/passes/` — `VehiclePassListCreateAPIView` (POST throttle: `pass_create` 30/h, GET unthrottled через `WriteOnlyScopedThrottle`)
- `/api/v1/passes/my/` — `MyVehiclePassListAPIView`
- `/api/v1/passes/<uuid:pass_id>/close/` — `CloseVehiclePassAPIView`
- `/api/v1/orgs/organizations/` — `OrganizationViewSet` list/create (not `/api/v1/orgs/`)
- `/api/v1/orgs/memberships/` — `OrganizationMembershipViewSet` (not `/api/v1/org-memberships/`)
- `/api/v1/site-settings/superadmin/orgs/` — `SuperAdminOrgsAPIView` (NOT `/site-settings/orgs/`)
- `/api/v1/auth/users/reset_password/` — Djoser password reset (PR-7 — раніше повертав 404 у prod, тепер активний з throttle 3/hour)
- `/api/v1/auth/users/reset_password_confirm/` — те саме
- `/api/v1/consent/` (POST) — `ConsentCreateAPIView` (GDPR ToS+Privacy)
- `/api/v1/consent/me/` (GET) — `ConsentMeAPIView` повертає `{tos, privacy, tos_current_version, privacy_current_version}` — frontend має слати `*_current_version` при POST, інакше modal зациклюється
- `/api/v1/health/` — `HealthCheckAPIView` (no auth, no throttle, DB+Redis ping → 200/503)
- `/api/v1/apartments/buildings/admin/` — `AdminBuildingListCreateAPIView` (GET list, POST create with optional nested `entrances: [{name, apartments_count}]`)
- `/api/v1/apartments/buildings/create/` — `BuildingCreateAPIView` legacy create (frontend hits this currently — both endpoints share the perform_create org auto-pin from PR-14)
- `/api/v1/apartments/buildings/<int:pkid>/` — `BuildingUpdateDestroyAPIView` (PATCH/DELETE)
- `/api/v1/apartments/buildings/<int:building_pkid>/entrances/admin/` — `AdminEntranceListCreateAPIView` (PR-14: nested list+create entrance, body `{name, apartments_count}`, max 500 units per entrance)
- `/api/v1/apartments/entrances/<uuid:id>/` — `AdminEntranceUpdateDestroyAPIView` (PR-14: PATCH rename / DELETE; DELETE → 409 if any unit has Residency)
- `/api/v1/apartments/entrances/<uuid:id>/grow/` — `AdminEntranceGrowAPIView` (PR-14: POST `{delta: N}`, append N apartments with sequential numbering, total cap 500)
- `/api/v1/site-settings/contacts/admin/` — `AdminContactListCreateAPIView` (PR-15: GET list, POST create. Body: `{name, role, position?, phone?, email?, telegram?, working_hours?, is_emergency?, is_active?, order?}`. `organization` НЕ writable — pin server-side через `perform_create` (Bug 1 prevention). `role` ∈ `manager|technician|guard|accountant|emergency|other`)
- `/api/v1/site-settings/contacts/admin/<int:id>/` — `AdminContactUpdateDestroyAPIView` (PR-15: PATCH update / DELETE. Cross-org → 404)
- `/api/v1/issues/assigned/stats/` — `MyAssignedStatsAPIView` (PR-16, GET, повертає flat dict з кількостями `Issue` по статусах для assigned issues, виключає self-reported. Запит ходить з LeftNavbar бейджа `Призначені заявки`. Status keys: `reported|accepted|in_progress|done|rejected`. UI використовує тільки `accepted` для бейджа.)

### PR-15 — Issue address visibility

`IssueSerializer` тепер містить `building_address` + `city` поля.  Backend
повертає реальні значення ТІЛЬКИ для:
- `request.user == issue.reported_by` (автор)
- `request.user == issue.assigned_to` (виконавець)
- `request.user.is_staff or request.user.is_superuser`

Усі інші читачі (наприклад, інший tenant у тій самій org з ID заявки)
отримують `null` для обох полів.  Це навмисна data minimisation —
номер квартири + точна адреса разом = достатньо для ідентифікації.

Frontend: `IssueDetails.tsx` рендерить адресу як subtitle нижче "Номер
квартири: X" тільки якщо `building_address` truthy.  `admin/issues`
table — те ж саме у subtitle колонки "Назва".

### PR-15 — `/profile?tab=my-issues` Bug 1 fallback

`MyIssuesListAPIView.get_queryset` тепер повертає рядки де
`reported_by=user AND (organization in user_orgs OR organization IS NULL)`.
Без NULL-fallback легасі дані (Issue з `org=NULL`) ховались від автора —
hot path tenant'а лишався порожнім.  Backfill через
`python manage.py backfill_issue_orgs` (resolve org з `unit.entrance.building`
або з reporter's first membership).

`IssueCreateSerializer.create` для надійності пинить org з `unit.entrance.building.organization`
коли user'у не вдалось знайти org через memberships (edge case для
superuser-creators).

## 🌐 Public pages (Next.js, без auth)

- `/terms` — `client/src/app/terms/page.tsx` (Умови користування, version 1.0)
- `/privacy` — `client/src/app/privacy/page.tsx` (Політика приватності, GDPR-aligned, version 1.0)
- `client/src/components/consent/ConsentGate.tsx` обгортає `(estate)/layout.tsx` —
  показує modal якщо `current=false` для ToS чи Privacy. POST шле
  `version: data.tos_current_version` (НЕ `data.tos?.version` — це баг hotfix 2026-04-26)

## 🏠 Desktop layout — Indigo Cabinet (since 2026-04-24)

The estate layout (`app/(estate)/layout.tsx`) was restructured:

- **Removed**: `<Navbar />` (top bar) and `<RightNavbar />` (popular posts sidebar) from desktop
- **Added**: `<CabinetTopbar />` — new 64px white topbar inside the content column (desktop only)
- **Redesigned**: `<LeftNavbar />` → indigo `#1E2761` sidebar with apartment chip, nav badges, user footer
- Mobile layout unchanged: `MobileHeader` (top) + `BottomNav` (bottom tabs)

`CabinetTopbar` live in `client/src/components/shared/navbar/CabinetTopbar.tsx`.

### Sidebar badges
`LeftNavbar` uses `.count` from paginated API responses (not `.results.filter(...)`) — results are capped at 10 per page and give wrong counts.

## 🔐 Auth gotchas

- `logged_in` cookie is **not** httpOnly — JavaScript can delete it via `deleteCookie("logged_in")` from `cookies-next`
- `handleLogout` in `useAuthNavigation` always calls `dispatch(setLogout())` + `deleteCookie("logged_in")` + `router.push("/login")` **before** the API call, so the user is always logged out client-side even if the server is unavailable
- `LogoutAPIView` has `throttle_classes = []` — logout is never rate-limited

## ⚠️ Known pitfalls

- `Profile.unit` FK **does not exist** (removed PR-11). Never use `profile.primary_unit` or `profile.unit`. Always resolve unit via `Residency.objects.filter(user=user, is_primary=True).first().unit`
- `on_announcement_created` signal was renamed to `on_announcement_saved` — any code that imports the old name will break
- **Cross-platform lockfile drift** — npm 10+ не матеріалізує optional peers, і macOS vs Linux резолвлять їх по-різному. Якщо Docker білд падає з `Missing: yaml@2.8.3 from lock file` — `yaml` зробили **прямою devDependency** у `package.json` (PR-7 hotfix). Не міняй на optional/transitive. Подібні pitfalls з іншими peer-deps можуть з'явитись — рішення те саме (explicit dep)
- **DRF `SimpleRateThrottle.THROTTLE_RATES` cache** — це **class-level** атрибут, заповнюється at-import-time з settings. Тести що змінюють rate через `override_settings` НЕ працюють — треба monkey-patch напряму (`SimpleRateThrottle.THROTTLE_RATES["scope"] = "..."`). Паттерн з DRF self-tests, див. `apps/users/tests/test_password_reset_throttle.py`
- **`ATOMIC_REQUESTS=True` + view test mocking** — Django відкриває savepoint через `connection.cursor()` ДО того як view виконається. Глобальний `patch.object(connection, "cursor", ...)` крашить transaction middleware → 500 замість очікуваного status. Замість цього патч **module-level reference** у view (`patch.object(apps.common.health, "connection", ...)`)
- **pytest `--import-mode=importlib`** обов'язково у `server/pytest.ini` — без нього кілька `apps/*/tests/__init__.py` пакетів конфліктують за ім'я `tests` (PR-1)
- **ConsentGate version sentinel** — у POST `/consent/` шли `data.tos_current_version`, НЕ `data.tos?.version` (echo'ить stale версію → modal зациклюється). Hotfix 2026-04-26

## 🛡️ Security headers (PR-8, since 2026-04-26)

Заголовки безпеки відправляє **Next.js** (`client/next.config.mjs:headers()`),
не Django. Користувачі ходять через Vercel, Django admin за secret URL —
окремий django-csp на бекенді не додавали.

Активні headers:
- `Content-Security-Policy` — baseline з `'unsafe-inline' 'unsafe-eval'` для
  Next.js хайдрейту (planned посилення через nonces). `connect-src`
  включає `api.apartmentos.org` + `*.up.railway.app` — **НЕ видаляй**, інакше
  всі API запити зломаються.
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

Lock-down тест `apps/common/tests/test_security_headers.py` падає, якщо
видалили `headers()` callback або зламали критичні директиви.

## 🗑️ Removed (видалено 2026-04-26 у PR-2)

Якщо натрапиш на згадку у legacy code/docs:
- `Navbar.tsx`, `RightNavbar.tsx`, `MobileNavbar.tsx`, `ThemeSwitcher.tsx` (видалені — заміщені indigo cabinet)
- `AdminDashboard.tsx` (заміщений `app/admin/page.tsx`)
- `TenantInfo.tsx` (0 imports)
- Shadcn UI: `form.tsx`, `menubar.tsx`, `sheet.tsx` (3 з 5 — `pagination` і `skeleton` ЗАЛИШЕНІ)
- 7 RTK hooks: `useGetUserQuery`, `useRefreshJWTMutation` (refresh через `baseApiSlice` напряму), `useGetAllIssuesQuery`, `useGetMyPostsQuery`, `useUnBookmarkPostMutation`, `useGetAllRepliesQuery`, `useGetTelegramBotQuery`
- TS type `RepliesResponse`
- Tailwind tokens: `googleBlue`, `richBlack`, `ballonWhite`, увесь `nordic.*` блок (12 ключів), `fontFamily.openSans`
- npm dep: `@radix-ui/react-menubar`
- `NotificationBell.tsx` ЗБЕРЕЖЕНИЙ як `@stub` placeholder для майбутньої in-app notifications фічі (НЕ рендериться)

## ♻️ Renamed

- `client/src/hooks/useUseProfile.ts` → `useUserProfile.ts` (typo fix, PR-4)
- `client/public/assets/logos/skandi-*.svg` → `apartmentos-*.svg` (PR-1, brand consistency)
- Local `IssueCard` у `rate-worker/page.tsx` → `ReviewIssueCard` (no shadow з `components/cards/IssueCard.tsx`)

## 📅 Changelog of infra decisions

- **2026-04-29 (PR-9..PR-12 + hotfixes — observability, monitoring, email infra)**:

  **Backend (PR-9, PR-10):**
  - **Telegram error alerts** — `apps.notifications.error_alerts.TelegramErrorHandler`
    логує 5xx помилки з `django.request` у приватний TG канал. Handler
    рівень ERROR (4xx WARN ігнорує), GDPR-safe (тільки `user.id`, без
    email/body/headers/querystring), HTML-escaped, fingerprint dedup
    через Redis (5-хв TTL), traceback truncate ≤4096 chars. Async
    через Celery — request thread не блокується.
  - **Scheduled health monitoring** — `apps.common.tasks.daily_health_status_task`
    (9:00 + 21:00 Europe/Kyiv, ALWAYS sends — "тиша = моніторинг здох")
    + `hourly_health_monitor_task` (silent OK, 🚨 only on degraded,
    hour-bucket dedup). Через Celery Beat. Reuse `run_health_checks()`
    helper з `/api/v1/health/`.
  - **Generic TG sender** — `send_telegram_message_task` у
    `apps/notifications/tasks.py` для health pings та інших
    operational notifications.

  **Backend (PR-11):**
  - **Org Report admin action** — superuser обирає org(s) у Django
    Admin → action **"📧 Згенерувати звіт..."** → за 1-2 хв на email
    приходить HTML звіт з KPI cards (буд/квартири/мешканці/заселені),
    SVG progress bar заселеності + ASCII fallback, список активних
    `_default_features()`, placeholder Тариф/Trial з yellow background.
    Async через Celery, multi-select = N окремих листів.
  - Permission gates: `is_superuser` only, requires non-empty
    `request.user.email`. Email — HTML-only через `EmailMultiAlternatives`,
    inline CSS, table-based layout, max-width 600px.

  **Backend (PR-12):**
  - **Email infra: SMTP → Resend HTTP API.** Custom backend
    `apps.common.email_backends.ResendEmailBackend` через офіційний
    `resend` Python SDK (без django-anymail wrapper). Conditional
    у `production.py`: якщо `RESEND_API_KEY` set → Resend HTTP, else
    SMTP fallback. Top-level `EMAIL_BACKEND=djcelery_email...` лишається
    (async dispatch), міняється тільки `CELERY_EMAIL_BACKEND`.
  - **Чому міграція:** Railway egress блокує SMTP — `smtp.resend.com:587`
    і `:465` обидва timeout-ять (TCP can't establish). HTTP API на
    порту 443 нормально проходить.
  - **Чому direct SDK не django-anymail:** один файл ~120 LOC, повний
    контроль над payload mapping, менший surface для security review,
    no extra dependency layer.

  **Hotfixes:**
  - **MERGE-PR9.sh heredoc apostrophe trap** — `<<'EOF'` всередині
    `$(cat ...)"` падає на `Telegram's`/`won't`/`dedup'd`. Виправлено
    через temp file pattern (`mktemp` + `git commit -F`).
  - **PR-12 stale .pyc** — Python не інвалідував `base.cpython-312.pyc`
    після видалення anymail з settings → `ModuleNotFoundError`. Fix:
    `find -name __pycache__ -exec rm -rf` у скрипті перед pytest.
  - **PR-12 wrong commit message** — git commit якимось чином узяв
    template з parable-web-wdio (chromedriver). Fix: `FIX-PR12-COMMIT.sh`
    з soft reset + правильний message через temp file.

  **Tests:** 853 → 878 passed (+25 нових: 23 Telegram alerts/health
  monitoring + 22 org report + 25 email backend).

  **Manual ops (Railway env vars):**
  - `ERROR_ALERTS_TG_BOT_TOKEN`, `ERROR_ALERTS_TG_CHAT_ID` — на ОБОХ
    Web + Worker сервісах
  - `RESEND_API_KEY=re_...`, `DEFAULT_FROM_EMAIL=noreply@apartmentos.org` —
    ТЕЖ на ОБОХ. Без `RESEND_API_KEY` на Worker — fallback до SMTP →
    timeout. Це важливий gotcha — кожен Railway сервіс має свій
    набір env vars.
  - Resend domain `apartmentos.org` верифіковано (SPF+DKIM+DMARC у
    Cloudflare DNS) — `noreply@apartmentos.org` працює як from-адреса.

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

- **2026-04-18 (seed_demo rewrite)**: Backend shipped the full
  `DEMO_SEED_PLAN.md` implementation: 7 seed modules under
  `apps/common/seed/`, scoped `reset_demo_scope` with HARD GUARD on
  superusers and a 12-test safety suite, orchestrator CLI with
  `--reset`, `--dry-run`, and `--passwords-from-env`. 22 backend tests
  cover idempotency + aggregate invariants; full pytest suite stays
  green (368 passed). With that in place:
  - Deleted the e2e `global-setup.ts` self-seed path and
    `fixtures/api-helpers.ts`'s `ensureIssuesSeeded` /
    `ensureTenantApartment` — no longer needed.
  - Removed `authTest.skip()` health guards from
    `admin-create-resident`, `access-control`, `admin-issue-status`,
    `assign-issue-flow`, `issue-detail-ui`, `issue-priority-visibility`,
    `issue-submission`, `issue-admin-flow`. Tests now trust
    `seed_demo`'s output directly.
  - The two old backend 500s (`/profiles/admin/all/` and
    `/profiles/user/my-profile/` for tenant) were symptoms of the
    seed gaps; the new seed binds every tenant/resident to a valid
    unit so the serializers no longer hit null dereferences.

- **2026-04-24 (feature batch: issue review + TG news + fixes)**:
  - **Mutual issue review**: `IssueReview` model, `POST /api/v1/issues/<uuid>/review/`, `GET /api/v1/issues/<uuid>/reviews/`. After issue is `done`, author rates worker, worker rates author. Frontend: `IssueReview` types in `index.d.ts`, `useReviewIssueMutation` + `useGetIssueReviewsQuery` in `issueApiSlice`, `StarRating` component + review section in `IssueDetails.tsx`
  - **TG notify on news**: `notify_subscribers` BooleanField on `News` model + `notify_subscribers_news` Celery task. Admin forms (AdminPosts + `admin/news/page.tsx`) have toggle checkbox
  - **Rating visibility fix**: `About.tsx` — `average_rating` shown only when `isWorker` (not to tenants)
  - **Complaint form**: `reported_person_name` free text field (was FK username lookup). `CreateReportForm.tsx` updated, `ReportCreateSchema.ts` updated
  - **Sidebar labels**: `/request-pass` → "Створити перепустку", `/my-passes` → "Мої перепустки"
  - **Passes delete**: `DeleteVehiclePassAPIView` — owner-only delete (removed `is_admin` bypass)
  - **Test fixes**: `News.__str__` added, annotation QuerySets got `.order_by("-created_at")` (UnorderedObjectListWarning), org test URLs fixed to `/api/v1/orgs/organizations/` + `/api/v1/orgs/memberships/`

- **2026-04-24 (cabinet redesign + bug fixes)**:
  - Desktop layout switched from top-navbar + white sidebar to indigo sidebar + CabinetTopbar
  - `KpiCard` updated: `text-4xl` number + "Переглянути →" action text
  - `MyPassesView` redesigned: filter tabs (Активні/Архів) + `ResidentPassCard` with monospace plate
  - `news/page.tsx` refactored: pinned section + `NewsCard` component
  - Bug: `IssueCreateAPIView.perform_create` used `profile.primary_unit` (removed PR-11) → fixed to use `Residency` lookup
  - Bug: sidebar badge counters used paginated `.results.filter()` → fixed to use `.count`
  - Bug: logout loop (429 → cookie not cleared → redirect to /welcome) → fixed with `deleteCookie` + eager client logout

- **2026-04-26 (8 PR + 3 hotfixes batch — tech-debt + production hardening)**:

  **Backend (PR-1, PR-3, PR-6):**
  - **RBAC refactor:** новий `apps/common/permissions.py` (IsGuard, IsTenant, IsStaff, IsGuardOrAdmin, IsStaffOrSuperUser alias). Видалено silent `except Exception: pass` з `passes/permissions.py` і `issues/views.py` — тепер тільки `Profile.DoesNotExist` з `logger.warning`
  - **JWT signing key fail-fast:** прибрано небезпечний default `"test-signing-key-change-in-production"` з `SIMPLE_JWT.SIGNING_KEY` — використовується `SECRET_KEY` напряму. Production вмирає з `ImproperlyConfigured` якщо `DJANGO_SECRET_KEY` env пропущено
  - **N+1 fixes:** `SuperAdminOrgsAPIView` (annotated `Count(memberships, filter=Q(is_active=True))`, 9→3 queries), `news/views.py` list (subquery + select_related, 14→5), `update_all_reputations` Celery task (`bulk_update`, 31→≤5)
  - **IDOR fix:** `IssueDetailAPIView.get_queryset()` тепер містить ПОВНИЙ auth predicate `Q(reported_by=user) | Q(assigned_to=user) | staff`. `get_object` більше не raise PermissionDenied — все що не у queryset → 404 (закриває info disclosure)
  - **`get_avatar_url` helper** винесено у `apps/profiles/utils.py` (3 копії з `posts/serializers.py` усунено). Конкретні exception types (`AttributeError`, `Profile.DoesNotExist`, `ValueError`) замість silent except
  - Видалено: `test_api_unit_cutover.py`, `ContentView.record_view` classmethod, дубль `isort` pin, 128 рядків disabled CI blocks
  - Розгорнуто `ConsentLog` модель (PR-5): `consent_type` (tos|privacy), `version`, `accepted_at`, `ip_address`, `user_agent`. Migration `0002`. Legacy `purpose/given/timestamp` поля збережені nullable

  **Frontend (PR-2, PR-4, PR-5):**
  - 9 мертвих компонентів видалено (~1176 рядків) — див. розділ "Removed"
  - 7 RTK hooks і 15 Tailwind tokens видалено
  - `ConsentGate` modal (`client/src/components/consent/ConsentGate.tsx`) обгортає `(estate)/layout.tsx` — блокує UI поки користувач не прийме поточні ToS+Privacy
  - `ConsentSummary` секція додана у профіль (вкладка "Про мене")
  - RTK slice `consentApiSlice.ts` — `useGetMyConsentQuery`, `useAcceptConsentMutation`
  - Public pages `/terms` і `/privacy` створені (раніше 404)

  **Production hardening (PR-7, PR-8, hotfixes):**
  - `/api/v1/health/` endpoint (DB+Redis ping). SSL redirect exempt у `production.py`. Per-service Railway healthcheck config (`docs/RAILWAY_SETUP.md`)
  - 4 burst rate limits: `issue_create` 20/h, `pass_create` 30/h, `post_create` 10/h, `rating_create` 30/h. `WriteOnlyScopedThrottle` для mixed read+write views
  - JSON structured logging у production (`python-json-logger`). Dev/test залишаються plain text
  - CSP + 4 classic security headers через `next.config.mjs`
  - CI security scan (`pip-audit` + `npm audit`, `continue-on-error`)
  - Dependabot активний (npm + pip + actions)
  - `.gitignore` більше не блокує `client/package-lock.json` (npm-only policy)
  - `SECURE_REFERRER_POLICY` правильна назва (раніше `REFERRER_POLICY` — phantom setting що не емітив header)
  - `OrganizationMembership` composite index `(user, is_active)` — hot path на кожному auth-request
  - Composite indices: `ContentView` `(content_type, object_id)` + `(user, -created)`, `Report` `(reported_user, -created)` + `(organization, -created)`
  - `<html lang>` виправлено `"en"` → `"uk"` (a11y/SEO)
  - **5 lock-down regex tests** у `apps/tests/test_railway_config.py`, `apps/common/tests/test_security_headers.py`, `apps/common/tests/test_logging_config.py`, `apps/common/tests/test_health.py::test_production_settings_exempts_health_from_ssl_redirect`

  **Documentation:**
  - `docs/RAILWAY_SETUP.md` — покроковий гайд (3 services + troubleshooting)
  - `docs/SECURITY_BACKLOG.md` — місце для CVE findings з CI scan
  - `docs/audits/` — 5 ad-hoc `.md` перенесено з кореня
  - `readme.md` — секції Health Check + Security Headers
  - `DEPLOYMENT_GUIDE.md` §9.1 оновлено

  **Tests:** 739 → 793 passed (+54 нових, 0 failed). Жодних regression.
