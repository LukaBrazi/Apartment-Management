# ApartmentOS — ОСББ Портал

Веб-портал для управління ОСББ та житловими комплексами. Мешканці подають заявки на обслуговування, переглядають новини та оголошення свого будинку, охорона керує перепустками для відвідувачів.

> **Архітектурний принцип:** Цей репозиторій — **ядро платформи**. Нові модулі (платежі, контакти, нотифікації) підключаються як окремі мікросервіси через змінні середовища.

## Можливості

### Ієрархія нерухомості
- **Будинок (Building)** → **Під'їзд (Entrance)** → **Квартира (Unit)**

### Заявки на обслуговування
- Категорії з SLA (норматив часу виконання у годинах)
- Автоматичний `due_at` та прапорець `is_overdue`
- Статуси: `reported → accepted → in_progress → done | rejected`
- Email-сповіщення при призначенні та вирішенні

### Новини порталу
- Портальні новини (адмін створює, всі мешканці бачать)
- Категорії, теги, обкладинка, закріплені новини, лічильник переглядів
- Підтримка зовнішніх посилань

### Оголошення будинку
- Прив'язані до конкретного будинку
- Мешканці бачать лише оголошення свого будинку

### Портал охорани
- Перепустки для відвідувачів (VehiclePass)
- Охорана закриває перепустку при в'їзді

### Профілі та соціальні функції
- Рейтинги технічного персоналу
- Публікації з тегами, голосуванням, закладками
- Звіти про порушення (5 скарг → блокування)

### Мікросервісна готовність
- Сторінки Платежі, Контакти — заглушки `<ComingSoon>` з `microserviceKey`
- Встановіть `NEXT_PUBLIC_{KEY}_URL` → сторінка автоматично підключить сервіс

## Технічний стек

| Шар | Технологія |
|-----|-----------|
| Backend | Django 4.2 + DRF |
| Database | PostgreSQL |
| Queue | Celery + Redis |
| Storage | MinIO (S3-compatible) |
| Frontend | Next.js 14 + TailwindCSS |
| State | Redux Toolkit + RTK Query |
| Forms | react-hook-form + Zod |
| Tests (unit) | pytest + factory_boy |
| Tests (E2E) | Playwright |
| Dev infra | Docker Compose + Nginx |

## Швидкий старт

```bash
# Клонувати
git clone <repo-url> && cd Django-Apartment-Management

# Запустити всі сервіси
make up

# Після першого запуску
make migrate && make seed
```

## Адреси після `make up`

| Сервіс | URL |
|--------|-----|
| Frontend | http://localhost:8080 |
| Django Admin | http://localhost:8080/django-admin/ |
| REST API | http://localhost:8080/api/v1/ |
| API Docs | http://localhost:8080/api/v1/redoc/ |
| MinIO | http://localhost:9090 |
| Mailpit | http://localhost:8025 |
| Flower | http://localhost:5555 |

## Тестування

```bash
make test        # unit тести (pytest)
make e2e-dev     # E2E тести (Playwright, піднімає стек)
make e2e         # повторно запустити E2E (стек вже живий)
```

## Облікові дані (seed)

| Роль | Email | Пароль |
|------|-------|--------|
| Диспетчер (staff) | dispatcher@demo.com | Demo1234! |
| Охоронець | guard@demo.com | Demo1234! |
| Мешканець | tenant@demo.com | Demo1234! |
| Мешканець 1 | resident1@demo.com | Demo1234! |

## Структура API

```
/api/v1/auth/        — аутентифікація (JWT cookie)
/api/v1/profiles/    — профілі користувачів
/api/v1/apartments/  — будинки, під'їзди, квартири
/api/v1/issues/      — заявки на обслуговування
/api/v1/news/        — новини порталу
/api/v1/posts/       — публікації + оголошення будинку
/api/v1/passes/      — перепустки охорани
/api/v1/ratings/     — рейтинги
/api/v1/reports/     — звіти про порушення
/api/v1/consent/     — GDPR consent (ToS + Privacy)
/api/v1/site-settings/ — налаштування сайту
/api/v1/health/      — health check (no auth)
```

## Health Check

`GET /api/v1/health/` — endpoint для load-balancer probes (Railway, k8s, uptime monitors).

- **Без авторизації** — `permission_classes = [AllowAny]`, без throttle
- Перевіряє: PostgreSQL (`SELECT 1`) + Redis (round-trip через cache)
- **200** якщо всі залежності OK, **503** якщо хоч одна впала

```bash
curl https://apartmentos.org/api/v1/health/
# {"status": "healthy", "checks": {"db": "ok", "cache": "ok"}}

# При проблемі:
# {"status": "unhealthy", "checks": {"db": "fail", "cache": "ok"}}
```

**Конфігурація на Railway** — **per-service у dashboard**, НЕ в `railway.toml`:

| Сервіс | Healthcheck Path |
|---|---|
| Web (Django) | `/api/v1/health/` |
| Celery Worker | _(порожнє — TCP probe)_ |
| Celery Beat | _(порожнє — TCP probe)_ |

> Чому per-service: якщо `healthcheckPath` стоїть у root `railway.toml`, він застосовується **до всіх 3 сервісів**, і Celery (без HTTP сервера) падає у "service unavailable". Покрокова інструкція — у [docs/RAILWAY_SETUP.md](docs/RAILWAY_SETUP.md).

Endpoint не експонує внутрішню інформацію (DB version, Redis URL тощо) — лише `ok`/`fail` на check.

## Error Alerts (PR-9)

Production 5xx помилки автоматично йдуть у приватний Telegram канал
з трейсбеком. Це cheap-tier заміна Sentry для startup-стадії.

- **Async** через Celery — request thread не блокується на TG API
- **Dedup** 5 хв per error fingerprint — flood-захист під час інцидентів
- **GDPR-safe** — тільки `user.id`, без email / body / headers / querystring
- **Опційне** — без env vars handler no-op (dev/CI чисті)
- **Тільки 5xx** — handler-level=ERROR, 4xx warnings не доходять у канал

Setup: див. [docs/ERROR_ALERTS_SETUP.md](docs/ERROR_ALERTS_SETUP.md).

**Health monitoring (PR-10):** окрім error trace, у той же бот приходять:
- 09:00 і 21:00 Europe/Kyiv — щоденний health ping (🟢 OK / 🟡 проблеми) —
  ALWAYS sends, щоб тиша на каналі сама була сигналом ("моніторинг живий")
- Щогодини у :00 — тихий моніторинг, alert тільки якщо `db` чи `cache` зламались

Працює через Celery Beat. Schedule entries у `CELERY_BEAT_SCHEDULE`
(`server/config/settings/base.py`), tasks у `apps.common.tasks`. Дедуплікація
по hour-bucket: Beat restart всередині однієї години не дублює alerts, але
кожна нова година може re-alert якщо проблема не пішла. Всі checks ділять
ту саму `run_health_checks()` функцію що `/api/v1/health/` — один source of
truth для "що значить healthy".

## Org Reports (PR-11)

Superuser може згенерувати HTML звіт по організації прямо з Django Admin
і отримати на email:

1. Зайти в `/django-admin/organizations/organization/`
2. Обрати одну або кілька організацій (checkbox-и)
3. Action dropdown → **📧 Згенерувати звіт і надіслати на пошту**
4. За 1-2 хв звіт прийде на email superuser-а (`request.user.email`).
   Multi-select = N окремих листів, по одному на org.

Звіт містить:
- KPI картки: будинки, квартири, мешканці, заселені квартири
- SVG progress bar заселеності (з ASCII fallback для текстових клієнтів)
- Список активних модулів (з default features `_default_features()`)
- Тариф / Trial — placeholder з yellow background до реалізації PR-12 / PR-13

Permission gates:
- Тільки `is_superuser` — інакше action віддає ERROR message
- Якщо у superuser `email=""` — action блокується з повідомленням
  "Додайте email через User Admin"

Технічно:
- Email рендериться як **тільки HTML** (`EmailMultiAlternatives` з одним
  HTML alternative). Plain-text fallback — коротка фраза "не підтримує HTML".
- Email-template — full inline CSS, table-based layout, max-width 600px,
  inline SVG для progress bar, без external resources (Gmail strips `<style>`,
  Outlook ламає flexbox)
- Celery task `send_organization_report_task` retry 3× з 30s delay на
  `SMTPException`/`OSError`. Missing org → log warning, no retry.

Файли:
- `server/apps/organizations/tasks.py` — `_gather_org_report_data`,
  `_list_active_features`, `send_organization_report_task`
- `server/apps/organizations/templates/organizations/email/org_report.html`
- `server/apps/organizations/admin.py` — `generate_org_report_email` action
- `server/apps/organizations/tests/test_org_report.py` — 22 TDD тести

## Email Backend (PR-12)

Транзакційні емейли йдуть через **Resend HTTP API** (`api.resend.com/emails`)
за допомогою кастомного backend `apps.common.email_backends.ResendEmailBackend`,
який сидить на офіційному [`resend`](https://github.com/resend/resend-python)
Python SDK. Дзвінки SMTP скасовано — Railway egress блокує
`smtp.resend.com:587` і `:465` (TCP handshake висне).

Flow:
- `email.send()` у Django код → `djcelery_email` кладе message на Celery queue
- Worker дістає task → `ResendEmailBackend` мапить `EmailMessage` у JSON-payload
  і POST'ить у Resend через офіційний SDK
- request thread ніколи не блокується

Чому власний backend, а не `django-anymail`: один файл (~120 LOC), повний
контроль над payload-мапінгом і нульовий зайвий depend-шар. Деталі — у
docstring `server/apps/common/email_backends.py`.

Feature flag: коли `RESEND_API_KEY` env var не задано → fallback на SMTP backend
(для local dev / CI / migration windows).

Setup на Railway — див. [docs/RAILWAY_SETUP.md](docs/RAILWAY_SETUP.md#resend-setup--email-через-http-api-pr-12).
Тести у `apps/common/tests/test_email_backend.py` покривають як lock-down
ланцюжка settings/requirements, так і unit-перевірки самого backend
(payload mapping, attachments, error handling).

## Security Headers (PR-8)

Заголовки безпеки відправляє **Next.js** (`client/next.config.mjs`),
не Django. Користувачі ходять через Vercel, Django admin живе за
секретним префіксом — окремий шар CSP на бекенді не потрібен.

Ввімкнено:

- **Content-Security-Policy** (baseline) — `default-src 'self'`,
  `frame-ancestors 'none'`, `object-src 'none'`. `script-src` поки
  з `'unsafe-inline' 'unsafe-eval'` через хайдрейт Next.js / React
  Refresh — посилення через nonces планується наступним PR.
  `connect-src` дозволяє `api.apartmentos.org` + Railway preview
  домени; **не видаляйте** інакше всі API-запити заблокуються.
- **X-Frame-Options: DENY**, **X-Content-Type-Options: nosniff**
- **Referrer-Policy: strict-origin-when-cross-origin**
- **Permissions-Policy** — забороняє camera / microphone / geolocation
  за замовчуванням

Lock-down тест `apps/common/tests/test_security_headers.py` падає,
якщо хтось випадково видалить `headers()` callback або зламає
важливу директиву.

## Billing (PR-13a)

Облік підписок, тарифних планів, add-ons і генерація invoices
для організацій. **Ядро без PDF / auto-billing / payment gateway** —
це фази PR-13b/c/d.

### Моделі (`apps/billing/`)

- **SubscriptionPlan** — каталог тарифів (Starter 5900, Business 14900,
  Professional 29900, Enterprise 59900). Поля `max_apartments` /
  `max_users` як `null` означають "без ліміту".
- **AddOn** — каталог add-ons (one_time або recurring_monthly).
- **OrganizationSubscription** — OneToOne на Organization. Сигнал
  `post_save` на створення Organization автоматично додає 60-денний
  trial на план Starter (якщо такий є у БД).
- **OrganizationAddOn** — активований add-on. Або FK на каталог AddOn,
  або кастомний модуль (`addon=null` + `custom_name` + `custom_price`).
  CheckConstraint унеможливлює "обидва порожні".
- **Invoice** — header. Поля `payer_*_snapshot` фіксують FOP-реквізити
  у момент створення (GAAP-style auditability — старі інвойси
  не змінюються при зміні settings). `invoice_number` авто-генерується
  у форматі `INV-YYYY-NNNNNN`.
- **InvoiceLineItem** — лінія з типом (`base_subscription`,
  `addon_recurring`, `addon_one_time`, `custom_module`,
  `proration_credit`/`charge`, `annual_discount`, `trial_credit`).

### Calculator service (`apps/billing/services/calculator.py`)

Три функції, всі повертають структури з `Decimal`:

- `calculate_recurring_invoice(org, period_start, period_end)` —
  base + recurring add-ons − 15% annual discount. Trial → all zeros +
  `trial_credit` line.
- `calculate_onboarding_invoice(org, addon_codes)` — сума one-time
  add-ons по списку catalog кодів.
- `calculate_proration_on_plan_change(org, new_plan, change_date)` —
  refund of unused old plan + prorated charge of new plan від
  change_date через `next_billing_at`.

### Admin actions

На `Organization` admin:
- **💰 Згенерувати monthly invoice (draft)** — створює draft Invoice
  + LineItems для кожної selected org з підпискою.
- **🔍 Preview next invoice** — dry-run, показує totals у messages.
- **🆕 Створити onboarding invoice…** — інтермедіат сторінка з
  checkbox-ами one-time add-ons.

На `Invoice` admin:
- **✅ Approve & email superuser** — переводить draft → approved і
  надсилає HTML body на `request.user.email` (superuser-only).
  **Ніколи** на email клієнта — інвойси перевіряє CEO вручну.

### Soft-warn limits

`apps/billing/signals.py` слухає `post_save` на:
- `apartments.Unit` → перевіряє `plan.max_apartments`
- `organizations.OrganizationMembership` → перевіряє `plan.max_users`

Якщо ліміт перевищено — Telegram message через
`send_telegram_message_task`. **Без hard block** — лише попередження.

### Org Report integration (PR-11 → PR-13a)

`_gather_org_report_data` тепер повертає реальні keys:
`subscription_plan_name`, `mrr_uah`, `is_in_trial`,
`trial_days_remaining`, `active_addons`. Шаблон `org_report.html`
відображає Trial yellow-block якщо trial активний, інакше — MRR
у великому шрифті + список активних add-ons.

### Manual ops після deploy

```bash
python manage.py migrate billing
python manage.py loaddata billing_initial   # 4 plans + 8 addons
```

Railway env vars (Web AND Celery Worker):

```
INVOICE_PAYER_LEGAL_NAME=ФОП Андрієнко Дмитро Володимирович
INVOICE_PAYER_TAX_ID=<ІПН або ЄДРПОУ>
INVOICE_PAYER_IBAN=UA...
INVOICE_PAYER_BANK_NAME=
INVOICE_PAYER_TAX_NOTE=Без ПДВ. Спрощена система оподаткування, 3 група, 5%.
INVOICE_DUE_DAYS=10
```

Lock-down regex тести (`apps/billing/tests/test_seed_lockdown.py`)
стережуть, щоб ціни у `billing_initial.json` не мутували випадково
під час rebase.

## Ліцензія

BSL-1.1 — дивіться LICENSE.
