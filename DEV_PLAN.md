# Dev Plan: Рейтинг / Скарга / Оцінка заявки

**Branch:** `main` (бандл фіксів)
**Created:** 2026-04-24

## Задача 1 — Рейтинг видимий тільки персоналу
- [ ] 1. About.tsx: обгорнути `average_rating` в isWorker-guard

## Задача 2 — Скарга: вільний текст замість username
- [ ] 2. Backend: Report.reported_person_name CharField + міграція
- [ ] 3. Backend: ReportSerializer — username опціональний, додати reported_person_name
- [ ] 4. Frontend: ReportCreateSchema, CreateReportForm, types, apiSlice

## Задача 3 — Взаємна оцінка після закриття заявки
- [ ] 5. Backend: модель IssueReview + міграція
- [ ] 6. Backend: серіалайзер + views (POST review, GET reviews) + URL
- [ ] 7. Backend: TDD тести
- [ ] 8. Frontend: types + RTK Query
- [ ] 9. Frontend: IssueDetails — форма оцінки після закриття

## Definition of Done
- [ ] Всі кроки виконано, pytest зелений
- [ ] DEV_PLAN.md видалено після merge

---

# Dev Plan: TG notify toggle у формах новин та оголошень

**Branch:** `main` (бандл фіксів)
**Created:** 2026-04-24

## Задача
Додати чекбокс «Сповістити підписників у Telegram» до двох адмін-форм:
1. Оголошення ЖК (AdminPosts.tsx) — поле вже є в моделі, лише фронтенд
2. Новини порталу (admin/news/page.tsx) — поле потрібне скрізь

## Кроки

- [ ] 1. Backend: `notify_subscribers` у моделі `News` + міграція
- [ ] 2. Backend: поле у `NewsAdminSerializer`
- [ ] 3. Backend: `get_news_target_chat_ids` у `notifications/utils.py`
- [ ] 4. Backend: Celery-задача `notify_subscribers_news`
- [ ] 5. Backend: виклик задачі у `NewsAdminListCreateAPIView.post()`
- [ ] 6. Backend: pytest-тести
- [ ] 7. Frontend: типи `AnnouncementCreateData` + `NewsCreateData`
- [ ] 8. Frontend: toggle у `AdminPosts.tsx`
- [ ] 9. Frontend: toggle у `admin/news/page.tsx`

## Definition of Done
- [ ] Обидва toggle у формах (default=false)
- [ ] Pytest зелені
- [ ] DEV_PLAN.md видалено після merge

---

# Dev Plan: Fix — клік по аватару відкриває профіль

**Branch:** `fix/avatar-profile-link`
**Created:** 2026-04-24

## Задача
Клік по аватару/юзер-чіпу не відкриває профіль у двох місцях:
1. `CabinetTopbar.tsx` — юзер-чіп є `<div>`, без `<Link>`
2. `LeftNavbar.tsx` — аватар у футері є `<div>`, без `<Link>`

`AuthAvatar.tsx` (mobile dropdown) вже має посилання на `/profile` — не чіпаємо.

## Кроки

- [x] 1. `CabinetTopbar.tsx` — обгорнути юзер-чіп у `<Link href="/profile">`
- [x] 2. `LeftNavbar.tsx` — обгорнути аватар + ім'я у `<Link href="/profile">`

## Definition of Done
- [ ] Клік по аватару → `/profile` (десктоп + сайдбар)
- [ ] Hover-стан помітний
- [ ] PR змерджено в main
- [ ] DEV_PLAN.md видалено

---

# Dev Plan: Оновлення дизайну згідно Design Bundle (Telegram + Design System)

Джерело: `apartmentos-design-system` — design bundle з claude.ai/design.
Ключові файли: `TelegramSettings.jsx`, `Primitives.jsx`, `colors_and_type.css`, `ui_kits/tenant-cabinet/`.

---

## ЧАСТИНА 1 — TelegramSettings: повний редизайн

Поточний компонент функціональний але візуально бідний — прості checkboxes, звичайна кнопка.
Дизайн показує 3 стани × 2 платформи (desktop + mobile compact).

### 1.1 Стан A: не підключено (`DefaultPanel`)

- [x] Замінити іконку `Send` на справжній Telegram SVG-лого (синє коло + paper plane)
- [x] Додати бейдж "Не підключено" (сірий `#F1F5F9 / #64748B`)
- [x] Двоколонковий layout desktop: зліва QR-код, справа кроки
- [x] QR-код: декоративний SVG з logo TG у центрі + підпис "Дійсний 10 хвилин"
- [x] Кроки з нумерованими колами (indigo `#1E2761` bg, white text)
- [x] CTA-кнопка "Відкрити Telegram" — indigo `#1E2761`, повна ширина, з TG лого
- [x] Секція-превʼю нижче "Що ви будете отримувати" (4 типи, disabled)

### 1.2 Стан B: очікування підтвердження (`WaitingPanel`)

- [x] Центрований TG лого у колі `#CADCFC`
- [x] Крутиться SVG-кільце (`strokeDasharray="18 14"`, animation `tgspin 1.6s linear infinite`)
- [x] Заголовок "Очікуємо підтвердження…"
- [x] Текст з @{bot_username} та token (витягується з deep_link URL)
- [x] Кнопки: "Скасувати" + "Відкрити Telegram знову"
- [x] Polling кожні 3с — без змін

### 1.3 Стан C: підключено (`ConnectedPanel`)

- [x] Аватар-літера + green checkmark overlay
- [x] Бейдж "Підключено" (зелений `#DCFCE7 / #2D8A4E`)
- [x] Дата підключення (з `created_at`, умовно)
- [x] Кнопка "Відʼєднати" — danger-outline
- [x] Секція "Типи сповіщень" з Toggle-рядками (3 типи з backend)
- [x] "Тихі години" блок (dashed border) — UI-only
- [x] Лічильник увімкнених: бейдж "X із 3"

---

## ЧАСТИНА 2 — Backend: нові поля для сповіщень

Дизайн передбачає 4 типи, backend має 3. Потрібно розширити.

- [x] Міграція: додати поля до `TelegramProfile`:
  - `notify_emergency` (BooleanField, default=True)
  - `notify_visits` (BooleanField, default=False)
  - `telegram_username` (CharField, nullable) — зберігати при /start
- [x] Оновити `TelegramStatusSerializer` — включити нові поля
- [x] Оновити `TelegramSettingsView` — приймати нові поля в PATCH
- [x] Оновити тип `TelegramStatus` у `client/src/types/index.d.ts`
- [x] Оновити `TelegramSettingsData` інтерфейс
- [x] Написати тести для нових полів (TDD)

---

## ЧАСТИНА 3 — Design Tokens: оновлення Tailwind конфігу

Привести `tailwind.config.ts` у відповідність до `colors_and_type.css`.

- [x] Перевірити поточний `tailwind.config.ts` — які кольори вже є
- [x] Додати/оновити CSS custom properties у `globals.css`:
  ```css
  --indigo-900: #1E2761;
  --indigo-200: #CADCFC;
  --blue-500: #4A90D9;
  --nordic-navy: #1C2B3A; /* майбутня палітра */
  --nordic-teal: #3D7A8A;
  /* ... */
  ```
- [x] Радіуси: `--radius-lg: 16px` як стандарт для карточок
- [x] Тіні: `--shadow-sm`, `--shadow-md` — стандартизувати, додано `--shadow-lg`
- [x] Типографіка: Inter cyrillic subset додано, fallback stack розширено

---

## ЧАСТИНА 4 — Компоненти: Toggle, TelegramLogo

- [x] Новий `Toggle.tsx` у `client/src/components/ui/` — w-11 h-6, indigo on, анімований thumb
- [x] Новий `TelegramLogo.tsx` у `client/src/components/shared/` — SVG paper-plane, props: size, mono

---

## ЧАСТИНА 5 — Мобільна адаптація (compact mode)

Дизайн має `compact` prop для всіх станів — менші відступи, шрифти, іконки.

- [x] На viewport < 768px показувати compact layout:
  - QR замість grid → вертикальний stack (md: breakpoint)
  - QR блок прихований на mobile (hidden md:flex)
  - Розміри іконок, кнопок, відступів — зменшені (md: responsive classes)
- [ ] Перевірити в DevTools iPhone SE / 375px

---

## ЧАСТИНА 6 — Перевірка і QA

- [ ] Проганяти pytest після backend змін (notify_emergency, notify_visits)
- [ ] Playwright E2E: перевірити що всі 3 стани відображаються коректно
- [ ] Ручна перевірка: resident → "Сповіщення" вкладка → всі стани
- [ ] Перевірити dark mode (компонент повинен виглядати коректно)

---

## Пріоритети виконання

| # | Крок | Складність | Вплив |
|---|------|-----------|-------|
| 1 | TelegramSettings redesign (стан A, B, C) | середня | 🔥 високий |
| 2 | Toggle.tsx + TelegramLogo.tsx компоненти | низька | 🔥 потрібне для п.1 |
| 3 | Backend: notify_emergency, notify_visits, telegram_username | середня | середній |
| 4 | Design tokens у globals.css | низька | середній |
| 5 | Мобільна адаптація | середня | середній |
| 6 | QA та тести | середня | 🔥 обовʼязково |

**Починати з пп.1–2 (frontend, без backend).**
Пп.3 — окремий PR після.

---

# Dev Plan: Telegram Notifications — Issues + Announcements

**Branch:** `feat/telegram-notifications-triggers`
**Created:** 2026-04-24

## Задача
Реалізувати Telegram сповіщення:
- Зміна статусу заявки → reporter + assigned_to
- Призначення виконавця → посилання на заявку
- Новини → чекбокс + confirmation dialog + scope-aware розсилка

---

## ЧАСТИНА А — Заявки

- [x] A1. `notify_tenant_issue_status_changed` — додати сповіщення `assigned_to`:
  - Якщо `issue.assigned_to` є і має профіль `notify_issues=True` → відправити те саме повідомлення
  - Не дублювати якщо reporter == assigned_to

- [x] A2. `notify_worker_assigned` — додати посилання на заявку:
  - `{PLATFORM_PUBLIC_URL}/issue/{issue.id}` в тіло повідомлення
  - Fallback: якщо `PLATFORM_PUBLIC_URL` не задано — не додавати лінк (не падати)

- [x] A3. Тести (TDD):
  - `test_status_change_notifies_assigned_to` — assigned_to отримує сповіщення при зміні статусу
  - `test_status_change_no_duplicate_if_reporter_is_assignee`
  - `test_worker_assigned_message_contains_link`
  - `test_worker_assigned_no_link_if_no_platform_url`

---

## ЧАСТИНА Б — Новини (Announcements)

- [x] B1. Модель `Announcement` — додати поля:
  - `notify_subscribers` (BooleanField, default=False)
  - `entrance` (FK to Entrance, nullable)
  - `organization` (FK to Organization, nullable — для org-wide оголошень)
  - `building` — зроблено nullable
  - Міграція: `0003_announcement_org_entrance_notify.py`

- [x] B2. Утиліта `get_announcement_target_chat_ids(announcement, org)`:
  - `entrance` → фільтрувати через `user__residencies__unit__entrance` (Residency, PR-11)
  - `building` (без entrance) → всі org-підписники
  - ні те ні інше → весь ЖК (org-wide)
  - Фільтр: `is_active=True, notify_announcements=True` (без occupation filter)

- [x] B3. `notify_building_tenants_announcement` — розширено:
  - Використовує нову утиліту замість хардкоду `occupation="tenant"`
  - Надсилає тільки якщо `announcement.notify_subscribers=True`
  - Org визначається з `building.organization` або `announcement.organization`

- [x] B4. Сигнал `on_announcement_saved` — оновлено (було `on_announcement_created`):
  - Запускає task тільки якщо `notify_subscribers=True` при створенні
  - При оновленні: запускає якщо `notify_subscribers` змінився `False→True`
  - pre_save: кешує старе значення `notify_subscribers`

- [x] B5. Admin форма `AnnouncementAdmin`:
  - Додано `notify_subscribers`, `entrance`, `organization` у `fields`
  - `save_model` override: показує кількість потенційних отримувачів через `messages.warning`

- [x] B6. Тести написані (TDD red phase → green після реалізації):
  - `test_announcement_notify_false_no_task_fired`
  - `test_announcement_scope_entrance`
  - `test_announcement_scope_building`
  - `test_announcement_scope_org_wide`

---

## Definition of Done
- [x] Всі кроки виконано
- [x] `pytest server/` зелений (665 passed, 4 pre-existing failures не пов'язані)
- [x] PR змерджено в main
- [ ] DEV_PLAN.md видалено після merge ← (залишено — є активний план по дизайну вище)
