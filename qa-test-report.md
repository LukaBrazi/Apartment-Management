# 🧪 QA Test Report — Skandi Apartments

> **Дата запуску:** 2026-03-21
> **Браузер:** Chromium (Playwright)
> **Тип тестів:** E2E Functional + Negative/Validation
> **PM:** Project Manager Agent

---

## 📊 Загальна статистика

| Метрика | Значення |
|---------|---------|
| ✅ Passed | **70** |
| ❌ Failed | **29** |
| 📋 Total | **99** |
| 📉 Pass Rate | **70.7%** |
| 📈 Fail Rate | **29.3%** |
| ⏱️ Час виконання | ~9.7 хвилин |

> ⚠️ **Висновок:** Pass rate 70.7% є нижчим за приийнятний поріг (≥ 90%). Реліз у поточному стані **не рекомендований**.

---

## 🔴 Провалені тести — Functional (12 тестів)

### 🏢 Admin CRUD Operations

| # | Файл | Тест | Пріоритет |
|---|------|------|-----------|
| 1 | `admin-create-building.spec.ts:15` | admin creates building → building appears in list | 🔴 Critical |
| 2 | `admin-create-resident.spec.ts:17` | admin creates resident → resident appears in list | 🔴 Critical |
| 3 | `admin-create-worker.spec.ts:18` | admin creates worker → worker appears in list | 🔴 Critical |

**Аналіз:** Три тести на базові CRUD-операції адміна — всі провалились. Швидше за все спільна причина: або проблема з авторизацією адміна, або змінився API endpoint / структура форм. Потребує першочергового розслідування.

---

### 📋 Issue (Заявки) Flow

| # | Файл | Тест | Пріоритет |
|---|------|------|-----------|
| 4 | `admin-issue-status.spec.ts:13` | admin changes issue status → status updated in system | 🔴 Critical |
| 5 | `admin-issue-status.spec.ts:73` | status change is verified via API — returns updated status | 🔴 Critical |
| 6 | `issue-admin-flow.spec.ts:12` | tenant creates issue → issue appears in admin panel | 🔴 Critical |
| 7 | `assign-issue-flow.spec.ts:10` | admin assigns issue to guard → guard sees it in assigned-issues tab | 🟠 High |

**Аналіз:** Весь flow заявок не працює — ні створення мешканцем, ні зміна статусу адміном, ні призначення робітнику. Можлива регресія у API `/issues/` або у логіці прав доступу.

---

### 📰 Posts & Announcements

| # | Файл | Тест | Пріоритет |
|---|------|------|-----------|
| 8 | `post-flow.spec.ts:11` | resident creates post → post appears on welcome page | 🟠 High |
| 9 | `post-flow.spec.ts:33` | post is accessible via API after creation | 🟠 High |
| 10 | `announcement-flow.spec.ts:10` | staff creates announcement → it appears in admin posts list | 🟠 High |

**Аналіз:** Публікації не створюються або не відображаються. Можлива проблема з API `/posts/` або `/announcements/`.

---

### 🚗 Guard & Pass

| # | Файл | Тест | Пріоритет |
|---|------|------|-----------|
| 11 | `guard-close-pass.spec.ts:9` | guard closes a vehicle pass → pass status becomes closed | 🟠 High |

**Аналіз:** Охоронець не може закрити пропуск. Можлива проблема з роллю `guard` або endpoint `/passes/{id}/close/`.

---

### 🔗 Regression / Navigation

| # | Файл | Тест | Пріоритет |
|---|------|------|-----------|
| 12 | `regression-bugs.spec.ts:96` | navigating to /profile?tab=my-issues shows Мої заявки tab content | 🟡 Medium |
| 13 | `regression-bugs.spec.ts:118` | navbar 'Мої заявки' link points to /profile with tab param | 🟡 Medium |

**Аналіз:** Таб `my-issues` у профілі не активується через URL параметр. Регресія у frontend роутингу або логіці табів.

---

## 🟠 Провалені тести — Negative / Validation (17 тестів)

### 🏢 Admin Building Validation

| # | Файл | Тест | Пріоритет |
|---|------|------|-----------|
| 14 | `admin-building-validation.spec.ts:80` | non-staff user cannot create building — 403 | 🔴 Critical |

**Аналіз:** Non-staff user може створювати будівлі — критична вразливість авторизації.

---

### 👤 Admin Resident / Worker Validation

| # | Файл | Тест | Пріоритет |
|---|------|------|-----------|
| 15 | `admin-resident-validation.spec.ts:47` | invalid email format — shows Ukrainian error | 🟠 High |
| 16 | `admin-worker-validation.spec.ts:46` | invalid email — shows Ukrainian error | 🟠 High |
| 17 | `admin-worker-validation.spec.ts:118` | duplicate email — server returns Ukrainian error toast | 🟠 High |
| 18 | `admin-worker-validation.spec.ts:138` | API rejects worker creation by non-staff — 403 | 🔴 Critical |

**Аналіз:** Дві проблеми: (1) валідація email не показує повідомлення українською, (2) non-staff може створювати workers — security issue.

---

### 📋 Issue Validation

| # | Файл | Тест | Пріоритет |
|---|------|------|-----------|
| 19 | `issue-validation.spec.ts:17` | empty form submission — shows Ukrainian error feedback | 🟠 High |
| 20 | `issue-validation.spec.ts:50` | title too short — shows Ukrainian validation error | 🟠 High |
| 21 | `issue-validation.spec.ts:70` | submitting issue without apartment — shows Ukrainian error toast | 🟠 High |

**Аналіз:** Форма заявки не валідує дані або не показує помилки українською мовою.

---

### 🚗 Pass Validation

| # | Файл | Тест | Пріоритет |
|---|------|------|-----------|
| 22 | `pass-validation.spec.ts:17` | empty form submission — shows Ukrainian error feedback | 🟠 High |
| 23 | `pass-validation.spec.ts:35` | past date — rejected with Ukrainian error | 🟠 High |
| 24 | `pass-validation.spec.ts:74` | API rejects past-date pass — returns 400 | 🔴 Critical |
| 25 | `pass-validation.spec.ts:99` | unauthenticated pass creation returns 401 | 🔴 Critical |

**Аналіз:** Критично: API приймає запити від неавторизованих користувачів і не відхиляє пропуски з минулою датою. Security + business logic issue.

---

### 📝 Post Validation

| # | Файл | Тест | Пріоритет |
|---|------|------|-----------|
| 26 | `post-validation.spec.ts:17` | empty form submission — shows Ukrainian error feedback | 🟠 High |
| 27 | `post-validation.spec.ts:35` | missing body — shows Ukrainian validation error | 🟠 High |
| 28 | `post-validation.spec.ts:66` | missing title — shows Ukrainian validation error | 🟠 High |
| 29 | `post-validation.spec.ts:85` | unauthenticated post creation returns 401 | 🔴 Critical |

**Аналіз:** API приймає пости від неавторизованих користувачів — security issue. Форма публікацій не валідує поля.

---

## 🚨 Класифікація за пріоритетом

| Пріоритет | К-сть | Баги |
|-----------|-------|------|
| 🔴 Critical (Blocker) | **9** | Admin CRUD, 403 auth bypass, 401 pass/post, API date validation |
| 🟠 High | **16** | Validation messages, flows, email errors |
| 🟡 Medium | **4** | Navigation regression, UI tabs |

> ❌ **9 Critical блокерів** — реліз заблокований до їх виправлення.

---

## 🔍 Кореневі причини (Root Cause Analysis)

### 1. 🔐 Проблеми авторизації / безпеки (5 тестів)
Тести: `admin-building-validation:80`, `admin-worker-validation:138`, `pass-validation:74`, `pass-validation:99`, `post-validation:85`

**Симптом:** API не повертає 403/401 для неавторизованих/непривілейованих запитів.

**Ймовірна причина:** Відсутні або некоректні `permission_classes` на Django REST Framework viewsets. Можливо, `IsAuthenticated` / `IsAdminUser` декоратори видалені або закоментовані.

**Рекомендація:** Перевірити `permissions.py` та `views.py` у backend.

---

### 2. 🗣️ Відсутність українських повідомлень про помилки (8 тестів)
Тести: валідація resident, worker, issue, pass, post forms

**Симптом:** Форми або не показують помилки, або показують їх не українською.

**Ймовірна причина:** `i18n` / `locale` не налаштований, або frontend validation messages захардкоджені англійською.

**Рекомендація:** Перевірити `zod` / `react-hook-form` error messages, переконатись що всі тексти через `t()` або locale-файли.

---

### 3. 📋 Admin CRUD не працює (3 тести)
Тести: `admin-create-building`, `admin-create-resident`, `admin-create-worker`

**Симптом:** Після створення сутність не з'являється у списку.

**Ймовірна причина:** Зміна структури API response, або тест очікує елемент який рендериться інакше (зміна CSS-класу / data-testid).

**Рекомендація:** Запустити тести з `--headed` та перевірити Network tab — чи повертає API 201.

---

### 4. 🔄 Весь Issues flow зламаний (4 тести)
Тести: `issue-admin-flow`, `admin-issue-status` x2, `assign-issue-flow`

**Симптом:** Заявки не створюються або не оновлюються.

**Ймовірна причина:** Регресія у `/api/issues/` endpoint або зміна полів форми.

**Рекомендація:** Перевірити останні коміти до `IssueViewSet` та моделі `Issue`.

---

### 5. 🗂️ Frontend navigation regression (2 тести)
Тести: `regression-bugs.spec.ts:96`, `:118`

**Симптом:** URL параметр `?tab=my-issues` не активує таб.

**Ймовірна причина:** Зміна у компоненті профілю — `useSearchParams()` не читає `tab` або логіка умов змінилась.

---

## 📋 Баг-трекер

| ID | Файл тесту | Severity | Компонент | Статус |
|----|-----------|----------|-----------|--------|
| BUG-001 | admin-create-building | 🔴 Critical | Admin / Buildings API | 🔵 Open |
| BUG-002 | admin-create-resident | 🔴 Critical | Admin / Users API | 🔵 Open |
| BUG-003 | admin-create-worker | 🔴 Critical | Admin / Workers API | 🔵 Open |
| BUG-004 | admin-issue-status (x2) | 🔴 Critical | Issues API | 🔵 Open |
| BUG-005 | issue-admin-flow | 🔴 Critical | Issues / Tenant UI | 🔵 Open |
| BUG-006 | admin-building-validation | 🔴 Critical | Auth / Permissions | 🔵 Open |
| BUG-007 | admin-worker-validation (403) | 🔴 Critical | Auth / Permissions | 🔵 Open |
| BUG-008 | pass-validation (API 400 + 401) | 🔴 Critical | Passes API | 🔵 Open |
| BUG-009 | post-validation (401) | 🔴 Critical | Posts API | 🔵 Open |
| BUG-010 | assign-issue-flow | 🟠 High | Issues / Guard UI | 🔵 Open |
| BUG-011 | announcement-flow | 🟠 High | Announcements | 🔵 Open |
| BUG-012 | post-flow (x2) | 🟠 High | Posts UI + API | 🔵 Open |
| BUG-013 | guard-close-pass | 🟠 High | Guard / Passes | 🔵 Open |
| BUG-014 | admin-resident-validation | 🟠 High | Validation / i18n | 🔵 Open |
| BUG-015 | admin-worker-validation (email + dup) | 🟠 High | Validation / i18n | 🔵 Open |
| BUG-016 | issue-validation (x3) | 🟠 High | Issues Form / i18n | 🔵 Open |
| BUG-017 | pass-validation (UI x2) | 🟠 High | Pass Form / i18n | 🔵 Open |
| BUG-018 | post-validation (UI x3) | 🟠 High | Post Form / i18n | 🔵 Open |
| BUG-019 | regression-bugs (x2) | 🟡 Medium | Profile / Tabs | 🔵 Open |

---

## ✅ Що пройшло (70 тестів)

70 тестів успішно пройшли, що свідчить про стабільну роботу:
- Базова авторизація (login/logout) — ✅
- Перегляд списків (будівлі, мешканці, пропуски) — ✅
- Загальна навігація по сайту — ✅
- Більшість UI рендерингу — ✅

---

## 🛠️ Action Plan для команди

### 🔴 Негайно (Sprint blocker — до кінця дня)
1. **Backend Dev:** Перевірити `permission_classes` на всіх ViewSets — Buildings, Workers, Passes, Posts
2. **Backend Dev:** Перевірити валідацію дати у `/passes/` — API має повертати 400 на минулу дату
3. **Backend Dev:** Розслідувати регресію у `/issues/` endpoint

### 🟠 Цього спринту (High priority)
4. **Frontend Dev:** Перевірити Ukrainian error messages у всіх формах (zod schemas / i18n)
5. **Frontend Dev:** Виправити `/profile?tab=my-issues` — `useSearchParams` логіка
6. **Frontend Dev:** Перевірити `/posts/` та `/announcements/` flows

### 🟡 Наступний спринт (Medium)
7. **QA:** Повторне тестування після фіксів
8. **QA:** Додати тести на edge cases що не покриті

---

## 🏁 Вердикт

| | |
|--|--|
| **Статус релізу** | ❌ **ЗАБЛОКОВАНО** |
| **Причина** | 9 Critical блокерів, pass rate 70.7% < 90% |
| **Умова розблокування** | Всі 9 Critical (BUG-001–009) виправлені + пройдено regression |
| **Відповідальний** | Backend Dev (permissions) + Frontend Dev (i18n, routing) |
| **Наступний QA run** | Після виправлення Critical багів |

---

*📅 Звіт підготовлено: 2026-03-21 | 🤖 QA Аналіз від PM Agent — Skandi Apartments*
