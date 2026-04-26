# Dev Plan: Tech-Debt Cleanup & Production-Ready Refactor

**Created:** 2026-04-26
**Strategy:** 6 послідовних PR, кожен на окремій feature-branch
**Audit reference:** Tech-debt audit, 2026-04-26 (zhukuymosya team — Architect + Reviewer)

## Задача

Production-ready clean-up та refactoring ApartmentOS на основі tech-debt аудиту.

**Поза скоупом:** Django 4.2 → 5.x upgrade, Pillow major bump, Tailwind `nordic.*` повний refactor (684 hex-classes), full GDPR (marketing/cookies banner), pipeline restructure CI.

**Тех. обмеження:**
- Push у `main` — лише CEO; команди тільки готують PR на feature-гілках
- Git операції — лише з Mac terminal (не зі sandbox через `.git/index.lock`)
- TDD policy: red → green → refactor для всього нового коду
- npm only (preinstall guard блокує pnpm/yarn)
- Multi-tenant org-scoping в кожному queryset
- Django 4.2 + DRF + Celery + Redis (без bump'у у цьому батчі)

---

## Phase 1 — PR-1: Critical Security & Infra Fixes
**Branch:** `fix/critical-security`
**TDD:** так (permission tests + signing key fail-fast test)

### Кроки

- [x] 1.1 Прибрати рядок `client/package-lock.json` з `.gitignore:46`; закомітити поточний `client/package-lock.json` у репо
- [x] 1.2 (TDD) Написати failing-тести у новому `server/apps/common/tests/test_permissions.py`: `test_is_guard_when_profile_missing_returns_false_explicitly`, `test_is_tenant_when_profile_missing_returns_false_explicitly`, `test_is_staff_when_user_anonymous_returns_false`
- [x] 1.3 Створити `server/apps/common/permissions.py` з класами `IsGuard`, `IsTenant`, `IsStaff`, `IsGuardOrAdmin`, `IsStaffOrSuperUser` — без `except Exception: pass`, лише `Profile.DoesNotExist` з логом
- [x] 1.4 Замінити локальні permission-класи на імпорт з `apps.common.permissions` у `passes/permissions.py`, `passes/views.py`, `issues/views.py`. Старі файли видалити
- [x] 1.5 (TDD) Тест `test_jwt_signing_key_must_be_set`: assert що `SIMPLE_JWT["SIGNING_KEY"]` падає з `ImproperlyConfigured` коли `DJANGO_SECRET_KEY` не задано
- [x] 1.6 У `server/config/settings/base.py:335` прибрати fallback default для `SIMPLE_JWT["SIGNING_KEY"]` — використати `env.str("DJANGO_SECRET_KEY")` без default
- [x] 1.7 У `server/config/settings/storage_backends.py` додати docstring: "Dev-only — MinIO без TLS. НЕ використовувати у staging/production"; перейменувати клас на `LocalMinioS3Storage` для явності; перевірити що production імпортує `S3Boto3Storage` напряму
- [x] 1.8 Перейменувати `client/public/assets/logos/skandi-logo-full.svg`, `skandi-logo-full-dark.svg`, `skandi-mark.svg` → `apartmentos-logo-full.svg`, etc.; оновити шляхи у `MobileHeader.tsx:43-51`, `Navbar.tsx`, `LeftNavbar.tsx`
- [x] 1.9 Оновити `client/CLAUDE.md:1` — заголовок "Skandi Apartments" → "ApartmentOS"
- [x] 1.10 Видалити `EstateOS_Lead_Manager_Pack_UA.docx` з кореня проєкту
- [x] 1.11 Прогнати `pytest server/` — усі зелені; `npm run build` у `client/` — успіх
- [x] 1.12 Підготувати PR-1 список файлів і команди для CEO (Mac terminal)
- [x] 1.13 (bonus) Зафіксувати 2 pre-existing тестові баги, які стали видимими через `--import-mode=importlib`:
  - `apps/feedback/views.py` — winесено `send_feedback_notification_task` import з `perform_create()` на module-level (mock.patch працював на module attr)
  - `apps/issues/tests/test_reviewable_issues.py:54` — `entrance_number=1` → `name="1"` (модель `Entrance` має поле `name`, не `entrance_number`)
  - Результат: 751 passed, 0 failed

---

## Phase 2 — PR-2: Frontend Dead Code Removal
**Branch:** `chore/frontend-cleanup`
**TDD:** ні (видалення; покривається існуючими тестами + build)

### Кроки

- [ ] 2.1 Видалити мертві компоненти: `client/src/components/shared/navbar/{Navbar,RightNavbar,MobileNavbar,ThemeSwitcher}.tsx`
- [ ] 2.2 Видалити `client/src/components/admin/AdminDashboard.tsx`
- [ ] 2.3 Видалити `client/src/components/cards/TenantInfo.tsx`
- [ ] 2.4 Видалити невикористовувані Shadcn UI primitives: `client/src/components/ui/{pagination,skeleton,form,menubar,sheet}.tsx`
- [ ] 2.5 `NotificationBell.tsx` — НЕ видаляти. Прибрати з усіх renders (`CabinetTopbar.tsx:77`), додати JSDoc-коментар у файлі: "@stub — placeholder for future in-app notifications. Not rendered. See #<issue-id> when implemented."
- [ ] 2.6 Видалити мертві RTK hooks (експорти + endpoints): `useGetUserQuery` + `getUser` (authApiSlice.ts:54), `useRefreshJWTMutation` (authApiSlice.ts:57), `useGetAllIssuesQuery` (issueApiSlice.ts:81), `useGetMyPostsQuery` (postApiSlice.ts:125), `useUnBookmarkPostMutation` (postApiSlice.ts:133), `useGetAllRepliesQuery` (postApiSlice.ts:135), `useGetTelegramBotQuery` (telegramBotsApiSlice.ts:110)
- [ ] 2.7 Видалити мертвий тип `RepliesResponse` з `client/src/types/index.d.ts:109`
- [ ] 2.8 Видалити мертві Tailwind tokens з `client/tailwind.config.ts`: `googleBlue`, `richBlack`, `ballonWhite`, увесь блок `nordic.*` (12 ключів), `fontFamily.openSans`
- [ ] 2.9 Видалити npm-залежність `@radix-ui/react-menubar` з `client/package.json`; перегенерувати `package-lock.json` через `npm install` на Mac (sandbox не годиться)
- [ ] 2.10 Видалити артефакти: `Select` (порожній файл у корені), `client/public/next.svg`, `client/public/vercel.svg`
- [ ] 2.11 Виконати `npm run build` + `npm run lint` — обидва без warnings (нові warnings блокують merge)
- [ ] 2.12 Smoke check на dev: login → /welcome → sidebar → news → issue list → request-pass → admin (всі сторінки рендеряться без runtime error)
- [ ] 2.13 Підготувати PR-2 опис

---

## Phase 3 — PR-3: Backend Dead Code Removal
**Branch:** `chore/backend-cleanup`
**TDD:** ні (видалення)

### Кроки

- [ ] 3.1 Видалити `server/apps/tests/test_api_unit_cutover.py` (deprecated placeholder, 10 рядків)
- [ ] 3.2 Видалити `ContentView.record_view` classmethod (`server/apps/common/models.py:132-172`); підтвердити що `IssueDetailAPIView` (issues/views.py:374) сам використовує `ContentView.objects.get_or_create` напряму
- [ ] 3.3 У `server/requirements/local.txt:12` видалити дублюючий `isort==5.13.2` (вже у `base.txt:11`)
- [ ] 3.4 У `Makefile:117-118, 156-157` перейменувати MinIO bucket: `skandi-apartments` → `apartmentos-local`
- [ ] 3.5 У `.github/workflows/ci.yml` прибрати disabled `e2e` job (рядки 42-147, ~106 рядків) і закоментований `deploy` block (рядки 149-171, ~22 рядки). Залишити TODO-коментар у CI: "e2e + deploy — окремі workflows, плануються Q3 2026"
- [ ] 3.6 У `server/pytest.ini:7` змінити `testpaths` на `apps` (auto-discovery замість 5-рядкового whitelist)
- [ ] 3.7 Прогнати `pytest` — кількість зібраних тестів **не менше** ніж до зміни (regression check)
- [ ] 3.8 Підготувати PR-3 опис

---

## Phase 4 — PR-4: Stale Comments & Docs Cleanup
**Branch:** `chore/docs-cleanup`
**TDD:** ні (тільки коментарі/перейменування)

### Кроки

- [ ] 4.1 Оновити stale `profile.unit` коментарі (PR-11 spec) у backend:
  - `server/apps/issues/urls.py:22` — фразу "from request.user.profile.unit" → "from primary Residency"
  - `server/apps/issues/tests/test_issue_permissions.py:72` — docstring те саме
- [ ] 4.2 Оновити docstring `server/apps/common/seed/seed_posts.py:20` — `on_announcement_created` → `on_announcement_saved`
- [ ] 4.3 Оновити stale коментарі у frontend:
  - `client/src/components/forms/report-issue/CreateIssueForm.tsx:30-31, 81` — прибрати фразу про `request.user.profile.unit`
  - `client/src/types/index.d.ts:233-237` — JSDoc для `ReportIssueData`
  - `client/src/components/shared/navbar/MobileHeader.tsx:7,10` — прибрати згадку про `<Navbar />` (видалений) та notif bell (stub)
- [ ] 4.4 Перейменувати файл `client/src/hooks/useUseProfile.ts` → `useUserProfile.ts` (typo fix); оновити всі імпорти; зберегти exported name `useUserProfile`
- [ ] 4.5 У `client/src/app/(estate)/rate-worker/page.tsx:68` перейменувати локальний `IssueCard` → `ReviewIssueCard` (прибрати name shadow з `components/cards/IssueCard.tsx`)
- [ ] 4.6 Перенести ad-hoc `.md` з кореня в `docs/audits/`:
  - `MULTI_TENANT_AUDIT.md` → `docs/audits/multi-tenant-audit-2026-04.md`
  - `db-review.md` → `docs/audits/db-review-2026-04.md`
  - `devops-review.md` → `docs/audits/devops-review-2026-04.md`
  - `design-images-icons.md` → `docs/audits/design-images-icons.md`
  - `design-spec-personal-cabinet.md` → `docs/audits/design-spec-personal-cabinet.md`
  - Залишити в корені: `readme.md`, `DEPLOYMENT_GUIDE.md`, `TECH_STACK.md`, `SUPERADMIN_QUICKSTART.md`
- [ ] 4.7 Перевірити що в перенесених `.md` нема broken internal links (basic grep)
- [ ] 4.8 `npm run build` + `pytest` — обидва зелені після перейменувань
- [ ] 4.9 Підготувати PR-4 опис

---

## Phase 5 — PR-5: GDPR MVP — ToS & Privacy Consent
**Branch:** `feat/gdpr-consent-mvp`
**TDD:** так (повний цикл red→green→refactor)

### Backend

- [ ] 5.1 (TDD) Тести у `server/apps/common/tests/test_consent.py`:
  - `test_post_consent_creates_log_with_user_version_ip_ua`
  - `test_post_consent_requires_authentication_returns_401`
  - `test_post_consent_invalid_type_returns_400`
  - `test_get_consent_me_returns_latest_per_type`
  - `test_get_consent_me_returns_null_when_no_consent`
  - `test_consent_outdated_when_version_bumped`
  - `test_consent_log_immutable_no_update_endpoint`
- [ ] 5.2 Розширити `ConsentLog` модель у `server/apps/common/models.py`: `user` (FK), `consent_type` (`tos`/`privacy` choices), `version` (CharField), `accepted_at` (auto), `ip_address` (GenericIPAddressField), `user_agent` (TextField)
- [ ] 5.3 Створити міграцію `apps/common/migrations/00XX_consentlog_extend.py`
- [ ] 5.4 Додати у `server/config/settings/base.py`: `TOS_VERSION = env.str("TOS_VERSION", default="1.0")`, `PRIVACY_VERSION = env.str("PRIVACY_VERSION", default="1.0")`
- [ ] 5.5 Створити `ConsentSerializer` (validate `consent_type`, accept `version`)
- [ ] 5.6 `POST /api/v1/consent/` — `ConsentCreateAPIView` (permission: `IsAuthenticated`, capture IP + UA з request)
- [ ] 5.7 `GET /api/v1/consent/me/` — `ConsentMeAPIView` (повертає `{tos: {version, accepted_at, current: bool}, privacy: {...}}`)
- [ ] 5.8 Зареєструвати URL у `apps/common/urls.py` + `config/urls.py`
- [ ] 5.9 Django Admin: `ConsentLogAdmin` з фільтрами (consent_type, version, user__email), readonly_fields всі поля
- [ ] 5.10 Прогнати `pytest server/apps/common/tests/test_consent.py` — green

### Frontend

- [ ] 5.11 (TDD) Vitest/Jest тести для `ConsentGate.tsx` компонента та RTK hooks (якщо тестова інфраструктура існує; якщо ні — задокументувати в PR і покрити e2e у наступному спринті)
- [ ] 5.12 Створити `client/src/lib/redux/features/consent/consentApiSlice.ts` з `useGetMyConsentQuery`, `useAcceptConsentMutation`; tags для cache invalidation
- [ ] 5.13 Додати типи `Consent`, `ConsentType`, `ConsentMeResponse` у `client/src/types/index.d.ts`
- [ ] 5.14 Створити компонент `client/src/components/consent/ConsentGate.tsx` — modal-блокер: якщо `useGetMyConsentQuery` повертає null/outdated для будь-якого type → показує modal з checkboxes для ToS і Privacy, після прийняття дзвонить `useAcceptConsentMutation` для кожного
- [ ] 5.15 Інтегрувати `<ConsentGate />` у `client/src/app/(estate)/layout.tsx` — обгортає children, блокує рендер якщо consent потрібен
- [ ] 5.16 Settings page (existing user profile) — секція "Згоди": список ToS/Privacy version + accepted_at, без re-accept кнопки (immutable log)
- [ ] 5.17 `npm run build` зелений; manual smoke: новий tenant → login → бачить modal → accept → бачить /welcome
- [ ] 5.18 Підготувати PR-5 опис з міграцією + env vars `TOS_VERSION`/`PRIVACY_VERSION`

---

## Phase 6 — PR-6: Backend Architecture Refactors
**Branch:** `refactor/backend-architecture`
**TDD:** так (N+1 регресії + permission edge cases)

### Кроки

- [ ] 6.1 (TDD) Регресійний тест `server/apps/site_settings/tests/test_orgs_view_n_plus_1.py` — `assertNumQueries(<=2)` для `SuperAdminOrgsAPIView.get` з N organizations
- [ ] 6.2 Виправити N+1 у `server/apps/site_settings/views.py:61-75` — `.annotate(active_members=Count("memberships", filter=Q(memberships__is_active=True)))`
- [ ] 6.3 (TDD) Регресійний тест `server/apps/news/tests/test_news_n_plus_1.py` — assertNumQueries для `news/views.py:36-43`
- [ ] 6.4 Виправити N+1 у `server/apps/news/views.py:36-43` — інлайнити `read_ids` як subquery; прибрати зайвий `.order_by()` перед `.count()`
- [ ] 6.5 Винести `get_avatar_url` helper у `server/apps/profiles/utils.py`; замінити 3 копії у `posts/serializers.py` (рядки 110, 178, 501); прибрати silent `except Exception: return None` — логувати з `logger.warning` і повертати None лише на конкретні exceptions
- [ ] 6.6 (TDD) Тести `test_issue_detail_only_via_get_queryset` — tenant з тієї ж org але без права на issue отримує 404 (не 403)
- [ ] 6.7 Refactor `IssueDetailAPIView.get_queryset()` у `server/apps/issues/views.py:318-354` — перенести всю фільтрацію `Q(reported_by=user) | Q(assigned_to=user) | Q(staff)` у queryset; прибрати overlap з `get_object`
- [ ] 6.8 (TDD) Тест `test_update_all_reputations_uses_bulk_update` — assertNumQueries обмежений (1 SELECT + 1 UPDATE)
- [ ] 6.9 Refactor `server/apps/profiles/tasks.py:18-23` — `bulk_update` замість `for profile: profile.save()`
- [ ] 6.10 Прибрати silent except у `server/apps/posts/admin.py:36` — логувати з `logger.error`, показати warning admin-у через `messages.warning(request, ...)`
- [ ] 6.11 Прибрати silent except у `server/apps/tests/conftest.py:49-50, 55-58` — додати конкретні exception types з коментарями-причинами
- [ ] 6.12 Прогнати `pytest server/` — усі тести зелені, нові N+1 тести проходять
- [ ] 6.13 Підготувати PR-6 опис

---

## Definition of Done (per PR)

- [ ] Feature branch створено локально, base = свіжий `main`
- [ ] Усі checkbox-кроки фази виконано
- [ ] TDD цикл відпрацьовано для нового коду (PR-1, PR-5, PR-6)
- [ ] `pytest server/` зелений (Django)
- [ ] `npm run build` успішний (frontend, де змінювали)
- [ ] `npm run lint` без нових warnings
- [ ] Migration додана якщо змінювали модель (PR-5)
- [ ] PR-опис self-contained: що, чому, як тестувати, як rollback
- [ ] CEO рев'ю + merge у main з Mac terminal

## Definition of Done (overall — після всіх 6 PR)

- [ ] Усі 6 PR змерджено в main
- [ ] Production deploy на Railway пройшов CI
- [ ] Staging smoke-test: login (admin/tenant/guard) → create issue → request pass → news → admin views → consent gate (для нового user)
- [ ] Tech-debt re-audit показує < 5 high-priority items
- [ ] `DEV_PLAN.md` видалено з repo (chore commit)
