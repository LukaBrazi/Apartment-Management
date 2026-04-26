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

- [x] 2.1 Видалити мертві компоненти: `Navbar.tsx`, `RightNavbar.tsx`, `MobileNavbar.tsx`, `ThemeSwitcher.tsx`
- [x] 2.2 Видалити `AdminDashboard.tsx`
- [x] 2.3 Видалити `TenantInfo.tsx`
- [x] 2.4 Видалити **3 з 5** Shadcn primitives: `form.tsx`, `menubar.tsx`, `sheet.tsx`. ⚠️ `pagination.tsx` і `skeleton.tsx` ЗБЕРЕЖЕНО — використовуються активно (audit був помилковим)
- [x] 2.5 `NotificationBell.tsx` — JSDoc `@stub` додано; render у CabinetTopbar вже прибрано
- [x] 2.6 Видалено 7 мертвих RTK hooks
- [x] 2.7 Видалено мертвий тип `RepliesResponse`
- [x] 2.8 Видалено мертві Tailwind tokens
- [x] 2.9 Видалено `@radix-ui/react-menubar`; lockfile регенерується через `npm install` на Mac у merge-скрипті
- [x] 2.10 Видалено артефакти: `Select`, `next.svg`, `vercel.svg`
- [x] 2.11 `npm run lint` — 0 нових warnings; `tsc --noEmit` clean; `npm run build` на Mac у merge-скрипті
- [x] 2.12 Smoke check — manual після merge (responsibility CEO)
- [x] 2.13 PR-2 опис готовий

---

## Phase 3 — PR-3: Backend Dead Code Removal
**Branch:** `chore/backend-cleanup`
**TDD:** ні (видалення)

### Кроки

- [x] 3.1 Видалено `server/apps/tests/test_api_unit_cutover.py`
- [x] 3.2 Видалено `ContentView.record_view` classmethod + невикористані imports `Optional`, `IntegrityError`
- [x] 3.3 Видалено дубль `isort==5.13.2` з `requirements/local.txt`
- [x] 3.4 Makefile: `skandi-apartments` → `apartmentos-local` (4 заміни)
- [x] 3.5 Прибрано `e2e` job + закоментований `deploy` з `ci.yml` (~128 рядків); залишено однорядковий TODO
- [x] 3.6 `pytest.ini` testpaths → `apps` (auto-discovery), `--import-mode=importlib` збережено
- [x] 3.7 pytest до/після: 751/751 passed — zero regression
- [x] 3.8 Об'єднано з PR-4 у `chore/cleanup-batch`

---

## Phase 4 — PR-4: Stale Comments & Docs Cleanup
**Branch:** `chore/docs-cleanup`
**TDD:** ні (тільки коментарі/перейменування)

### Кроки

- [x] 4.1 Оновлено stale `profile.unit` коментарі (backend) у `issues/urls.py`, `tests/test_issue_permissions.py`
- [x] 4.2 `seed_posts.py` docstring: `on_announcement_created` → `on_announcement_saved`
- [x] 4.3 Оновлено stale коментарі у frontend: `CreateIssueForm.tsx`, `types/index.d.ts`, `MobileHeader.tsx`
- [x] 4.4 `useUseProfile.ts` → `useUserProfile.ts`; 3 імпорти оновлено (CabinetTopbar, LeftNavbar, AuthAvatar)
- [x] 4.5 Локальний `IssueCard` у rate-worker → `ReviewIssueCard` (3 references)
- [x] 4.6 Перенесено 5 ad-hoc `.md` у `docs/audits/`
- [x] 4.7 Internal links перевірено — broken links 0
- [x] 4.8 pytest 751 passed; tsc clean; lint 0 нових warnings
- [x] 4.9 Об'єднано з PR-3 у `chore/cleanup-batch`

---

## Phase 5 — PR-5: GDPR MVP — ToS & Privacy Consent
**Branch:** `feat/gdpr-consent-mvp`
**TDD:** так (повний цикл red→green→refactor)

### Backend

- [x] 5.1 (TDD) Тести у `server/apps/common/tests/test_consent.py`:
  - `test_post_consent_creates_log_with_user_version_ip_ua`
  - `test_post_consent_requires_authentication_returns_401`
  - `test_post_consent_invalid_type_returns_400`
  - `test_get_consent_me_returns_latest_per_type`
  - `test_get_consent_me_returns_null_when_no_consent`
  - `test_consent_outdated_when_version_bumped`
  - `test_consent_log_immutable_no_update_endpoint`
- [x] 5.2 Розширити `ConsentLog` модель у `server/apps/common/models.py`: `user` (FK), `consent_type` (`tos`/`privacy` choices), `version` (CharField), `accepted_at` (auto), `ip_address` (GenericIPAddressField), `user_agent` (TextField)
- [x] 5.3 Створити міграцію `apps/common/migrations/0002_extend_consentlog_for_gdpr_mvp.py`
- [x] 5.4 Додати у `server/config/settings/base.py`: `TOS_VERSION = env.str("TOS_VERSION", default="1.0")`, `PRIVACY_VERSION = env.str("PRIVACY_VERSION", default="1.0")`
- [x] 5.5 Створити `ConsentSerializer` (validate `consent_type`, accept `version`)
- [x] 5.6 `POST /api/v1/consent/` — `ConsentCreateAPIView` (permission: `IsAuthenticated`, capture IP + UA з request)
- [x] 5.7 `GET /api/v1/consent/me/` — `ConsentMeAPIView` (повертає `{tos: {version, accepted_at, current: bool}, privacy: {...}}`)
- [x] 5.8 Зареєструвати URL у `apps/common/urls.py` + `config/urls.py`
- [x] 5.9 Django Admin: `ConsentLogAdmin` з фільтрами (consent_type, version, user__email), readonly_fields всі поля
- [x] 5.10 Прогнати `pytest server/apps/common/tests/test_consent.py` — green (8 passed; full suite 759 passed)

### Frontend

- [x] 5.11 (TDD) Vitest/Jest відсутні у client/ — задокументовано у PR-описі; e2e покриття для ConsentGate перенесено у наступний спринт
- [x] 5.12 Створити `client/src/lib/redux/features/consent/consentApiSlice.ts` з `useGetMyConsentQuery`, `useAcceptConsentMutation`; tag `Consent` додано у `baseApiSlice.tagTypes`
- [x] 5.13 Додано типи `Consent`, `ConsentType`, `ConsentMeResponse` у `client/src/types/index.d.ts`
- [x] 5.14 Створено `client/src/components/consent/ConsentGate.tsx` — fixed-overlay modal з checkbox-ами для ToS і Privacy
- [x] 5.15 Інтегровано `<ConsentGate />` у `client/src/app/(estate)/layout.tsx` (всередині `EstateAuthGate`)
- [x] 5.16 `ConsentSummary` секція додана у `About.tsx` (таб "Про мене") — read-only список ToS/Privacy version + accepted_at + бейдж Актуальна/Застаріла
- [x] 5.17 `tsc --noEmit` clean, `npm run lint` 0 нових warnings; `npm run build` пропущено у sandbox (SWC arm64 без мережі) — виконається на Mac у MERGE-PR5.sh
- [x] 5.18 `MERGE-PR5.sh` готовий у корені репо (з повним commit message + список файлів)

---

## Phase 6 — PR-6: Backend Architecture Refactors
**Branch:** `refactor/backend-architecture`
**TDD:** так (N+1 регресії + permission edge cases)

### Кроки

- [x] 6.1 (TDD RED) `apps/site_settings/tests/test_orgs_view_n_plus_1.py` — RED показав 9 запитів (5 orgs × 1 count + baseline 4)
- [x] 6.2 (GREEN) `apps/site_settings/views.py` — `.annotate(active_members=Count("memberships", filter=Q(memberships__is_active=True), distinct=True))`. Після: 3 запити (constant)
- [x] 6.3 (TDD RED) `apps/news/tests/test_news_n_plus_1.py` — RED показав 14 запитів для 10 новин
- [x] 6.4 (GREEN) `apps/news/views.py` — `select_related("category") + prefetch_related("tags")`, `read_ids` як subquery, `.order_by()` перед `.count()`. Після: 5 запитів
- [x] 6.5 `apps/profiles/utils.py` створено з `get_avatar_url()`; 3 копії в `apps/posts/serializers.py` (TopPostSerialzier, ReplySerializer, BasePostSerializer) замінено на helper-call. Конкретні exception types: `(AttributeError, Profile.DoesNotExist)`, `(ValueError, AttributeError)`, з `logger.warning`
- [x] 6.6 (TDD RED) `apps/issues/tests/test_issue_detail_permission_edges.py` — RED показав 403 замість очікуваного 404 (information leak)
- [x] 6.7 (GREEN) `apps/issues/views.py` — `IssueDetailAPIView.get_queryset()` повна фільтрація `Q(reported_by) | Q(assigned_to)` (для не-staff), `get_object()` без PermissionDenied. Pre-existing test `test_detail_tenant_cannot_see_others_issue` оновлено з 403 → 404 (це фікс, не регресія)
- [x] 6.8 (TDD RED) `apps/profiles/tests/test_update_all_reputations_bulk.py` — RED показав 31 запит для 10 профілів
- [x] 6.9 (GREEN) `apps/profiles/tasks.py` — `bulk_update(fields=["reputation"], batch_size=200)`. Після: ≤5 запитів (constant)
- [x] 6.10 `apps/posts/admin.py` — `except Exception: pass` → `except (DatabaseError, ValueError)` + `logger.error` + `messages.warning(...)` admin-у
- [x] 6.11 `apps/tests/conftest.py` — `except Exception` (line 49) → `except (ModuleNotFoundError, ImportError, AttributeError)` з коментарем-причиною; `except RuntimeError` залишено як було (специфічний)
- [x] 6.12 `pytest`: 759 → **765 passed** (+6 нових тестів), 0 failed
- [x] 6.13 `MERGE-PR6.sh` — готовий direct-merge скрипт у корені

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
