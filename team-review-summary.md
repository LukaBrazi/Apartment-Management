# Team Review — Executive Summary
**Проєкт:** Skandi Apartments
**Дата:** 2026-03-21
**Статус:** Sprint Review — повний аудит командою

---

## ✅ Що зроблено за сесію

### 1. Особистий кабінет (Personal Cabinet)
- Дизайн-специфікація: `design-spec-personal-cabinet.md`
- Реалізовано компоненти:
  - `WelcomeHero.tsx` — аватар з ініціалами, Ukrainian date, skeleton loading
  - `QuickActions.tsx` — 4 кнопки швидких дій, горизонтальний скрол на мобільному
  - `SlaChip.tsx` — колірна індикація SLA (зелений/жовтий/червоний)
  - `PassesMiniPanel.tsx` — pending-пропуски на дашборді
  - `ResidentDashboard.tsx` — оновлено з усіма новими компонентами

### 2. Telegram Notifications App
Повністю реалізовано `server/apps/notifications/`:
- `models.py` — TelegramProfile + TelegramVerificationToken
- `tasks.py` — 5 Celery-тасків для всіх типів сповіщень
- `signals.py` — Django signals для Issue, VehiclePass, Announcement
- `views.py` — API для генерації токену, верифікації, налаштувань
- `urls.py` — 5 endpoint'ів
- `management/commands/run_bot.py` — polling bot з командами /start, /stop, /status
- `migrations/0001_initial.py` — міграція таблиць
- Зареєстровано в `settings/base.py`, `urls.py`, `requirements/base.txt`

---

## 🔴 Критичні проблеми (виправити негайно)

### [SECURITY] Credentials у git-репозиторії
**Файл:** `.envs/.local/` — PostgreSQL пароль, MinIO ключі, Django secret key у відкритому вигляді
```bash
git rm -r --cached .envs/.local/
echo ".envs/.local/" >> .gitignore
# + ротувати всі паролі
```

### [SECURITY] Mass Assignment — ескалація привілеїв
**Файл:** `server/apps/profiles/serializers.py`
Поле `occupation` writeable — будь-який мешканець може підвищити свої права до GUARD.
```python
# Прибрати "occupation" з UpdateProfileSerializer.fields
# або додати: read_only_fields = ["occupation"]
```

### [SECURITY] Немає валідації файлових завантажень
**Файл:** `server/apps/profiles/views.py`
Аватар приймається без перевірки mime-type/розміру — можливий upload шкідливих файлів.

### [SECURITY] JWT не інвалідується при logout
При `POST /auth/token/logout/` access token залишається валідним до закінчення TTL.
Рішення: Redis-blacklist токенів або скорочення access TTL до 5 хвилин.

---

## 🟠 Серйозні проблеми (виправити в наступному спринті)

### N+1 Query проблеми (DB Admin)
7 місць де ORM не використовує `select_related`/`prefetch_related`:
- `IssueSerializer.get_view_count` — count per record в циклі
- `PostSerializer.get_avatar` — окремий SELECT на кожен пост
- `AssignedIssuesListAPIView` — не робить prefetch для assigned_to + building
- `RatingsSerializer` — missing select_related("worker", "tenant")

### Відсутні DB індекси
12 полів без індексів, найкритичніші:
- `Issue.status`, `Issue.created_at` — часто фільтрується
- `VehiclePass.status`, `VehiclePass.tenant`
- `TelegramProfile.chat_id` (вже unique, але варто composite index)

### DevOps: `makemigrations` в entrypoint
**Файл:** `compose/local/server/start`
Автогенерація міграцій при кожному старті — небезпечно і некоректно.

### DevOps: Контейнер від root
Dockerfile не задає non-root USER — security risk при RCE.

### UX: PostCard grid-cols-2 ломає мобільний layout
**Файл:** `client/src/components/Posts/PostCard.tsx`
`grid-cols-2` без responsive breakpoints — контент перекривається на мобільному.

### UX: IssueCard `dark:text-lime-500` — конфлікт кольорів
Лаймовий текст на темному фоні — низька контрастність, не відповідає дизайн-системі.

---

## 🟡 Рекомендації (технічний борг)

### DevOps
- Немає `docker-compose.prod.yml` — деплой лише через Railway; не портабельно
- Gunicorn `--workers 2` захардкожено — повинно бути `$(nproc)` або env змінна
- Відсутній health check для Celery worker'ів
- Немає Sentry/error tracking для production
- CI не перевіряє тести перед merge в main

### Backend
- `Rating` не має `unique_together(tenant, worker)` — можливі дублікати оцінок
- `ContentView.object_id` — PositiveIntegerField замість BigIntegerField (мismatch з DEFAULT_AUTO_FIELD)
- Celery tasks не мають dead-letter queue для failed notifications
- Telegram bot використовує лише polling; для production треба webhook

### Frontend
- `as any` TypeScript casts в `ResidentDashboard.tsx` (sla_deadline) — треба розширити типи
- Announcements div має hover-стилі але не є клікабельним (href відсутній)
- Немає rate limiting на frontend форм сабмітах

---

## 📊 Пріоритетний план дій

| # | Задача | Пріоритет | Виконавець |
|---|--------|-----------|------------|
| 1 | Видалити .envs/.local/ з git + ротувати паролі | 🔴 Критично | DevOps |
| 2 | Прибрати occupation з writeable fields | 🔴 Критично | Backend |
| 3 | Додати валідацію file uploads | 🔴 Критично | Backend |
| 4 | Виправити N+1 queries (select_related) | 🟠 Серйозно | Backend/DB |
| 5 | Видалити makemigrations з entrypoint | 🟠 Серйозно | DevOps |
| 6 | Додати non-root USER в Dockerfile | 🟠 Серйозно | DevOps |
| 7 | Виправити PostCard mobile layout | 🟠 Серйозно | Frontend |
| 8 | Додати DB індекси | 🟡 Борг | DB Admin |
| 9 | JWT blacklist або скорочення TTL | 🟡 Борг | Backend |
| 10 | Написати тести для notifications app | 🟡 Борг | QA/Backend |

---

## 📁 Файли-артефакти

| Файл | Вміст |
|------|-------|
| `devops-review.md` | 20 пунктів DevOps аудиту |
| `db-review.md` | 18 пунктів: N+1, індекси, schema issues |
| `security-audit.md` | 15 вразливостей (4 критичні) |
| `ux-review.md` | 12+ UX/UI проблем |
| `design-spec-personal-cabinet.md` | Дизайн-специфікація кабінету |
| `pm-notifications-plan.md` | Архітектура + 20 задач Telegram |
| `pm-tracking.md` | Трекер виконання + критерії приймання |
