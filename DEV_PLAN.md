# Dev Plan: Оновлення дизайну згідно Design Bundle (Telegram + Design System)

Джерело: `apartmentos-design-system` — design bundle з claude.ai/design.
Ключові файли: `TelegramSettings.jsx`, `Primitives.jsx`, `colors_and_type.css`, `ui_kits/tenant-cabinet/`.

---

## ЧАСТИНА 1 — TelegramSettings: повний редизайн

Поточний компонент функціональний але візуально бідний — прості checkboxes, звичайна кнопка.
Дизайн показує 3 стани × 2 платформи (desktop + mobile compact).

### 1.1 Стан A: не підключено (`DefaultPanel`)

- [ ] Замінити іконку `Send` на справжній Telegram SVG-лого (синє коло + paper plane)
- [ ] Додати бейдж "Не підключено" (сірий `#F1F5F9 / #64748B`)
- [ ] Двоколонковий layout desktop: зліва QR-код, справа кроки
- [ ] QR-код: декоративний SVG з logo TG у центрі + підпис "Дійсний 10 хвилин"
- [ ] Кроки з нумерованими колами (indigo `#1E2761` bg, white text):
  - Крок 1: "Відскануйте QR-код / або натисніть кнопку на телефоні"
  - Крок 2: "Надішліть код підтвердження"
- [ ] Код підтвердження: monospace блок (`#F1F5F9` bg) + кнопка "Копіювати" (→ "Скопійовано" ✓)
  - Форматувати token з backend: перші 11 символів / або залишити як є
- [ ] CTA-кнопка "Відкрити Telegram" — indigo `#1E2761`, повна ширина, з TG лого
- [ ] Секція-превʼю нижче "Що ви будете отримувати":
  - 4 рядки toggle (preview, disabled до підключення)
  - Іконки + кольорові фони по типу (periwinkle / amber / red / green)
  - Написи: "Нові оголошення ОСББ", "Статус моїх заявок", "Аварійні повідомлення", "Візити гостей"

### 1.2 Стан B: очікування підтвердження (`WaitingPanel`)

**ЗАРАЗ ВІДСУТНІЙ** — показується Spinner + текст в тому самому блоці.

- [ ] Новий компонент `WaitingState` всередині TelegramSettings
- [ ] Центрований TG лого 64px у колі `#CADCFC`
- [ ] Крутиться SVG-кільце (`strokeDasharray="18 14"`, animation `tgspin 1.6s linear infinite`)
- [ ] Заголовок "Очікуємо підтвердження…"
- [ ] Текст: "Надішліть боту @{bot_username} код {token}"
- [ ] Кнопки: "Скасувати" (secondary) + "Відкрити Telegram знову" (primary)
- [ ] Polling кожні 3с — залишається без змін

### 1.3 Стан C: підключено (`ConnectedPanel`)

- [ ] Аватар з першою літерою імені користувача (indigo/teal bg) + green checkmark overlay
- [ ] @telegram_username якщо є, або "Telegram підключено"
- [ ] Бейдж "Підключено" (зелений `#DCFCE7 / #2D8A4E`)
- [ ] Дата підключення в monospace (з `created_at`)
- [ ] Кнопка "Відʼєднати" — danger-outline (`#FEE2E2 / #C0392B`, border)
- [ ] Секція "Типи сповіщень" з toggle-рядками (замінити checkboxes):
  - Custom Toggle: `width:44, height:26`, indigo коли on, `#E2E8F0` коли off, анімований кружок
  - Рядки: іконка (кольорове коло) + назва + опис + toggle
  - 3 типи з backend: issues / passes / announcements
- [ ] "Тихі години" блок (dashed border, `#F8FAFC` bg) — UI-only поки що, без backend
- [ ] Лічильник увімкнених: бейдж "X із 3"

---

## ЧАСТИНА 2 — Backend: нові поля для сповіщень

Дизайн передбачає 4 типи, backend має 3. Потрібно розширити.

- [ ] Міграція: додати поля до `TelegramProfile`:
  - `notify_emergency` (BooleanField, default=True)
  - `notify_visits` (BooleanField, default=False)
  - `telegram_username` (CharField, nullable) — зберігати при /start
- [ ] Оновити `TelegramStatusSerializer` — включити нові поля
- [ ] Оновити `TelegramSettingsView` — приймати нові поля в PATCH
- [ ] Оновити тип `TelegramStatus` у `client/src/types/index.d.ts`
- [ ] Оновити `TelegramSettingsData` інтерфейс
- [ ] Написати тести для нових полів (TDD)

---

## ЧАСТИНА 3 — Design Tokens: оновлення Tailwind конфігу

Привести `tailwind.config.ts` у відповідність до `colors_and_type.css`.

- [ ] Перевірити поточний `tailwind.config.ts` — які кольори вже є
- [ ] Додати/оновити CSS custom properties у `globals.css`:
  ```css
  --indigo-900: #1E2761;
  --indigo-200: #CADCFC;
  --blue-500: #4A90D9;
  --nordic-navy: #1C2B3A; /* майбутня палітра */
  --nordic-teal: #3D7A8A;
  /* ... */
  ```
- [ ] Радіуси: `--radius-lg: 16px` як стандарт для карточок
- [ ] Тіні: `--shadow-sm`, `--shadow-md` — стандартизувати
- [ ] Типографіка: перевірити що `Inter` підключений і є fallback

---

## ЧАСТИНА 4 — Компоненти: Toggle, TelegramLogo

- [ ] Новий `Toggle.tsx` у `client/src/components/ui/`:
  ```tsx
  <Toggle checked={bool} onChange={fn} disabled? />
  ```
  Дизайн: `w-11 h-6`, indigo коли on, slate-200 коли off, анімований thumb
- [ ] Новий `TelegramLogo.tsx` у `client/src/components/shared/`:
  - Props: `size`, `mono` (white vs branded)
  - SVG paper-plane з синім колом

---

## ЧАСТИНА 5 — Мобільна адаптація (compact mode)

Дизайн має `compact` prop для всіх станів — менші відступи, шрифти, іконки.

- [ ] На viewport < 768px показувати compact layout:
  - QR замість grid → вертикальний stack
  - Розміри іконок, кнопок, відступів — зменшені
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
- [ ] Всі кроки виконано
- [ ] `pytest server/` зелений
- [ ] PR змерджено в main
- [ ] DEV_PLAN.md видалено після merge
