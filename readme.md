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

## Ліцензія

BSL-1.1 — дивіться LICENSE.
