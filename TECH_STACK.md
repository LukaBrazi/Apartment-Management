# Tech Stack — Skandi Apartments

Пояснення кожної технології в проєкті: що вона робить і чому обрана саме вона.

---

## Архітектура одним реченням

Клієнт (Next.js) → Nginx → Django REST API → PostgreSQL, і паралельно Celery-воркери читають задачі з Redis та виконують фонові операції (email, Telegram-сповіщення).

---

## Backend

### Django 4.2

**Що робить:** Python веб-фреймворк — основа всього backend. Надає ORM для роботи з базою даних, систему міграцій, admin-панель, систему шаблонів, middleware, signals і командний інтерфейс (`manage.py`).

**Чому Django, а не Flask/FastAPI:**
- **ORM** — Django ORM дозволяє описувати структуру бази через Python-класи і автоматично генерує міграції. Для проєкту з 15+ моделями (User, Profile, Apartment, Issue, Rating, Report…) це критично — жоден SQL-файл вручну писати не треба.
- **Admin-панель** — готовий інтерфейс для управління даними без зайвого коду. Менеджер ЖК може переглядати мешканців, заявки, перепустки прямо через `/admin/` без окремого frontend.
- **Batteries included** — CSRF захист, email backend, static files, сигнали, permissions — все вже є. FastAPI це все потребує окремих бібліотек.
- **Зрілість** — Django існує з 2005 року, LTS-версія 4.2 підтримується до квітня 2026. Жодних сюрпризів у production.

---

### Django REST Framework 3.15

**Що робить:** Надстройка над Django для побудови REST API. Дає `APIView`, `GenericAPIView`, `ModelSerializer`, `permission_classes`, `authentication_classes`, `renderers`, `parsers`, `throttling`, `pagination`.

**Чому DRF, а не голий Django:**
- **Serializers** — автоматична валідація вхідних JSON-даних і серіалізація моделей у JSON. Без DRF потрібно писати цей код вручну для кожного endpoint.
- **Permission system** — `permission_classes = [IsAuthenticated]` або `[IsAdminUser]` одним рядком замість if-checks в кожному view.
- **Browsable API** — під час розробки кожен endpoint відкривається у браузері як HTML-форма. Зручно тестувати без Postman.
- **Generic views** — `ListAPIView`, `RetrieveAPIView`, `CreateAPIView` покривають 80% типових endpoints без написання коду.

---

### PostgreSQL + psycopg3

**Що робить:** Реляційна база даних. psycopg3 — Python-адаптер, через який Django ORM відправляє SQL-запити до PostgreSQL.

**Чому PostgreSQL, а не SQLite/MySQL:**
- **JSONB поля** — потенційно для динамічних метаданих без нових таблиць.
- **Повнотекстовий пошук** — `django-filter` + PostgreSQL full-text search для пошуку заявок, мешканців.
- **Constraint-based integrity** — `unique_together`, partial indexes, FK constraints на рівні БД. SQLite не підтримує concurrent writes і ряд обмежень.
- **Production-ready** — PostgreSQL витримує тисячі concurrent connections, ACID-транзакції, має row-level locking. SQLite — тільки для локальної розробки.
- **psycopg3 (не psycopg2)** — async-ready адаптер, підтримує connection pooling і pipeline mode для batch-операцій.

---

### Gunicorn (production)

**Що робить:** WSGI-сервер, який запускає Django application у production. Обробляє HTTP-запити в кількох процесах/воркерах паралельно.

**Чому Gunicorn, а не `runserver`:**
- Django `runserver` — single-threaded, без буферизації, без graceful restart. Тільки для розробки.
- Gunicorn запускає N worker-процесів (зазвичай `2 * CPU + 1`), кожен обробляє запит незалежно. Якщо один падає — інші продовжують працювати.

---

## Аутентифікація

### djangorestframework-simplejwt

**Що робить:** JWT (JSON Web Token) аутентифікація. При логіні видає два токени: `access` (живе 5 хв) і `refresh` (живе 1-7 днів). Access token додається до кожного API-запиту і перевіряється без звернення до БД.

**Чому JWT, а не сесії (Session-based auth):**
- **Stateless** — сервер не зберігає сесії. Масштабується горизонтально: будь-який сервер може перевірити токен без синхронізації.
- **HttpOnly cookies** — токени зберігаються в `httpOnly; Secure; SameSite=Lax` cookies, а не в localStorage. JavaScript не має доступу → XSS не може вкрасти токен.
- **Refresh rotation** — access token короткоживучий, refresh замінюється при кожному refresh-запиті. Якщо refresh вкрадено — він протухає і потрапляє в blacklist.
- **Token Blacklist** — simplejwt зберігає відкликані tokens в БД. Критично при GDPR erasure та logout.

---

### Djoser

**Що робить:** Набір готових DRF-endpoints для auth: реєстрація, логін, зміна пароля, скидання пароля через email, підтвердження email, JWT-refresh.

**Чому Djoser:** Не треба писати register/confirm/reset-password з нуля. Djoser покриває весь auth-lifecycle через конфіг у `settings.py`, а custom views (login з cookies, logout) тільки розширюють його.

---

### argon2-cffi

**Що робить:** Хешування паролів алгоритмом Argon2id (переможець Password Hashing Competition 2015).

**Чому Argon2, а не bcrypt/SHA:** Argon2id — memory-hard алгоритм. Навіть з GPU-фермою або ASIC brute-force мільйонів паролів на секунду — неможливий через вимогу великого обсягу RAM на кожен хеш. Django за замовчуванням використовує PBKDF2, який значно слабший проти GPU-атак.

---

## Асинхронна обробка

### Redis

**Що робить:** In-memory key-value store. Використовується в проєкті у двох ролях: message broker для Celery (черга задач) і cache backend (Django cache framework).

**Чому Redis:** Celery підтримує RabbitMQ, SQS, Redis як broker. Redis обраний тому, що він вже потрібен для кешування — одна інфраструктурна одиниця замість двох. Redis Pub/Sub дозволяє легко додати WebSocket-нотифікації в майбутньому.

---

### Celery + django-celery-beat

**Що робить:** Celery — розподілений task queue. Замість того щоб відправляти email або push-сповіщення синхронно (блокуючи HTTP відповідь), Django ставить задачу в чергу Redis → Celery-воркер забирає і виконує в фоні.

django-celery-beat додає **periodic tasks** (як cron): наприклад, щоденна перевірка прострочених SLA заявок або щотижневий дайджест.

**Чому Celery:**
- Email відправка через SMTP може займати 1-2 секунди. Без Celery — кожен API-запит, що тригерить email, чекав би відповіді SMTP-сервера.
- Telegram-сповіщення, PDF-генерація, масові розсилки — все виконується паралельно в воркерах без блокування API.

---

### Flower

**Що робить:** Web UI для моніторингу Celery. Показує активні воркери, виконані задачі, черги, помилки в реальному часі.

**Чому:** Без Flower неможливо знати чи виконується задача, чи вона зависла, скільки задач у черзі. Flower — observability для async layer.

---

## Зберігання файлів

### MinIO (local) / Cloudflare R2 (production)

**Що робить:** Object storage, S3-сумісний. Аватари, документи, зображення зберігаються не на диску сервера, а в object store. MinIO — self-hosted S3 для локальної розробки. Cloudflare R2 — production (S3-сумісний, без egress fees).

**Чому не на диску сервера:**
- Якщо сервер перезапускається або масштабується — файли на локальному диску недоступні для інших інстансів.
- R2 / S3 — replicated, durable (99.99%), дешевий. Cloudflare R2 має нульову плату за вихідний трафік.

---

### django-storages + boto3

**Що робить:** django-storages — Django storage backend для cloud (S3, GCS, Azure, R2). boto3 — AWS SDK для Python, через який django-storages комунікує з S3-сумісними сервісами.

**Чому:** Одна зміна в settings (`DEFAULT_FILE_STORAGE`) — і Django починає зберігати всі файли в R2 замість локального диску. Жодних змін у коді моделей або views.

---

### Pillow

**Що робить:** Python image processing бібліотека. Потрібна Django `ImageField` для валідації і ресайзу аватарів.

---

## Email

### Mailpit (local dev)

**Що робить:** Легкий SMTP-сервер для розробки. Перехоплює всі outgoing emails і показує їх у web UI на `localhost:8025`. Жоден email не відправляється реальному отримувачу під час розробки.

**Чому не gmail/sendgrid в dev:** Не треба реальних credentials, не треба хвилюватись про spam-фільтри чи акаунти. Mailpit запускається в Docker і готовий за секунду.

---

### django-celery-email

**Що робить:** Перенаправляє `django.core.mail.send_mail()` в Celery-задачу. Email відправляється асинхронно — Django не чекає підтвердження від SMTP.

---

## Документація API

### drf-spectacular

**Що робить:** Автоматично генерує OpenAPI 3.0 специфікацію (YAML/JSON) з DRF views, serializers і permission classes. Надає Swagger UI і Redoc для інтерактивної документації.

**Чому:** Без drf-spectacular документацію API треба писати вручну і підтримувати в актуальності. drf-spectacular читає код і генерує spec автоматично — документація завжди відповідає реальним endpoints.

---

## Telegram Bot

### python-telegram-bot

**Що робить:** SDK для роботи з Telegram Bot API. Дозволяє відправляти повідомлення мешканцям, сповіщення про статус заявок, оновлення перепусток прямо в Telegram.

**Чому Telegram, а не тільки email:** Значна частина мешканців читає Telegram активніше за email. Push-сповіщення в Telegram — instant і не потрапляє в spam. Інтеграція опціональна (мешканець сам підключає свій Telegram).

---

## Утиліти Backend

**django-environ** — читає `.env` файл і надає `env()` helper для settings.py. Не треба hardcode credentials в коді; production, staging і local мають різні `.env` файли.

**django-autoslug** — автоматично генерує URL slug для моделей (Post, Report, News) з вказаного поля. Якщо slug вже зайнятий — додає суфікс. Жодного ручного коду.

**django-taggit** — M2M теги для постів форуму. Один рядок у моделі (`tags = TaggableManager()`) замість окремої Tags-моделі і всієї логіки вручну.

**django-filter** — URL query params (`?status=reported&priority=high`) автоматично конвертуються в ORM-фільтри. Декларативна конфігурація замість ручного `request.GET.get(...)` в кожному view.

**django-countries** — поле `CountryField` з ISO 3166-1 кодами і формами. Для профілю мешканця (країна походження).

**django-phonenumber-field** — валідація номерів телефонів у форматі E.164 (`+380501234567`). Підтримує всі країни через бібліотеку `phonenumbers`.

**django-cors-headers** — додає CORS заголовки (`Access-Control-Allow-Origin`) до відповідей Django. Без цього Next.js (порт 3000) не може звертатись до Django API (порт 8000) через браузерну same-origin policy.

**python-slugify** — utility для конвертації довільного тексту в URL-safe рядок. Підтримує кирилицю і транслітерацію.

---

## Frontend

### Next.js 14 (App Router)

**Що робить:** React-фреймворк від Vercel. App Router (Next 13+) дозволяє server-side rendering, server components, route handlers і layout-систему прямо в React.

**Чому Next.js, а не CRA/Vite + React:**
- **SSR / SSG** — сторінки рендеряться на сервері → швидкий First Contentful Paint і SEO-ready (важливо для публічних сторінок ЖК).
- **File-system routing** — папки в `app/` автоматично стають URL. Жодного manual router config.
- **Image optimization** — `next/image` автоматично конвертує зображення у WebP, lazy-load і responsive sizes.
- **API Routes** — якщо потрібен легкий proxy або BFF — без окремого сервера.

---

### TypeScript

**Що робить:** Статична типізація поверх JavaScript. Компілятор перевіряє типи під час розробки, а не в runtime.

**Чому TypeScript:** Проєкт має ~50+ типів (User, Profile, Apartment, Issue, Rating…). Без TypeScript — помилки типів знаходяться тільки після деплою. З TypeScript — IDE підсвічує невідповідності одразу при написанні коду. Особливо критично для RTK Query відповідей і form schemas.

---

### Redux Toolkit + RTK Query

**Що робить:** Redux Toolkit — сучасний Redux без boilerplate. RTK Query — data-fetching шар: автоматичне кешування відповідей API, background refetching, optimistic updates, invalidation тегів.

**Чому Redux + RTK Query, а не SWR/React Query:**
- Глобальний стан (auth user, site settings, поточний ЖК) зручно тримати в Redux store.
- RTK Query інтегрований з Redux — кеш API живе в тому ж store що й UI-стан.
- Tag-based invalidation: після `createIssue` → автоматично рефетчиться `getIssues`. Без ручного `queryClient.invalidateQueries(...)`.

---

### React Hook Form + Zod

**Що робить:** React Hook Form — performant форми без re-render на кожен keystroke. Zod — TypeScript-first schema validation бібліотека.

**Чому разом:** RHF відповідає за controlled input management, Zod — за validation rules (`z.string().min(3).max(255)`). `@hookform/resolvers/zod` з'єднує їх: схема Zod стає resolver-ом RHF-форми. Один source of truth для типів і правил валідації.

---

### TailwindCSS

**Що робить:** Utility-first CSS фреймворк. Стилі пишуться через класи прямо в JSX (`className="flex items-center gap-4 rounded-lg bg-white shadow-md"`).

**Чому Tailwind, а не Bootstrap/SCSS:**
- **Немає context switching** — стилі і компонент в одному місці. Не треба шукати `.issue-card` у CSS файлі.
- **Purge unused** — production build містить тільки використані utility classes. CSS bundle < 10 KB замість сотень.
- **Design system через config** — кольори, spacing, breakpoints описані в `tailwind.config.ts` і використовуються скрізь.

---

### Radix UI + shadcn/ui

**Що робить:** Radix UI — бібліотека headless UI примітивів (Dialog, Select, Tabs, DropdownMenu, Avatar…) з повною accessibility (WAI-ARIA). shadcn/ui — набір готових компонентів, побудованих на Radix + Tailwind, які копіюються прямо в проєкт (не npm-залежність).

**Чому:**
- Radix гарантує keyboard navigation, screen reader support і focus management. Писати це вручну — сотні рядків складного коду.
- shadcn/ui дає готовий дизайн — Button, Input, Card, Badge, Table — але повністю кастомізований через Tailwind. Не locked in у чийсь дизайн.

---

### Zod (окремо)

**Чому Zod, а не Yup/Joi:** TypeScript-first — Zod схема інферить TypeScript-тип автоматично (`z.infer<typeof schema>`). Не треба писати тип і schema окремо. Yup старший і менш type-safe.

---

### axios

**Що робить:** HTTP-клієнт. Використовується для запитів поза RTK Query (наприклад, авторизаційний interceptor для refresh token rotation).

**Чому axios поряд з RTK Query:** RTK Query покриває більшість запитів. Але для auth-flow (автоматичний refresh при 401) зручніший axios interceptor — він прозоро ретраює запит після оновлення токена.

---

### @tanstack/react-table

**Що робить:** Headless table library. Сортування, пагінація, фільтрація, row selection — логіка без UI. Рендеринг — наш Tailwind/shadcn.

**Чому:** Таблиці заявок, мешканців, рейтингів потребують сортування і пагінації. Писати це з нуля — тижні. react-table — де-факто стандарт для complex tables в React.

---

## Інфраструктура

### Docker + Docker Compose

**Що робить:** Контейнеризація кожного сервісу (Django, Next.js, PostgreSQL, Redis, MinIO, Nginx, Celery-worker, Celery-beat, Flower, Mailpit, Telegram Bot). Docker Compose описує всі сервіси і їх залежності в одному YAML файлі.

**Чому Docker:**
- `docker compose up` — весь стек запускається однією командою. Нові розробники не встановлюють PostgreSQL, Redis, MinIO локально.
- **Parite між середовищами** — local, staging, production використовують однакові Docker images. "Works on my machine" виключено.
- **Ізоляція** — кожен сервіс у своїй мережі, не конфліктує з іншими проєктами на машині.

---

### Nginx

**Що робить:** Reverse proxy перед Django і Next.js. Приймає всі HTTP/HTTPS запити, розподіляє на backend (`/api/*` → Gunicorn:8000) і frontend (`/*` → Next.js:3000). Відповідає за SSL termination, gzip compression, static files serving.

**Чому Nginx перед Gunicorn:** Gunicorn не вміє ефективно обслуговувати slow clients (повільні з'єднання тримають воркер зайнятим). Nginx буферизує запит повністю, потім одним fast-передає Gunicorn. Також Nginx віддає статику (JS, CSS, images) напряму без Django — набагато швидше.

---

## Інструменти розробки

**isort** — автоматичне сортування Python imports за PEP8 і проєктними правилами. `isort .` — всі файли за секунду.

**eslint + prettier** — лінтинг і форматування TypeScript/React коду. `eslint-config-next` + `eslint-plugin-tailwindcss` — специфічні правила для Next.js і Tailwind.

**date-fns** — lightweight утиліта для форматування дат на frontend. Альтернатива moment.js без 200 KB bundle size.

**lucide-react + @heroicons/react** — SVG іконки у вигляді React компонентів. Tree-shakeable — bundle містить тільки використані іконки.

---

## Схема взаємодії

```
Browser
  ↓ HTTPS
Nginx (80/443)
  ├── /api/*      → Gunicorn → Django → PostgreSQL
  │                                   → Redis (cache)
  │                                   → MinIO/R2 (files)
  └── /*          → Next.js (SSR/CSR)

Django signals / Views
  → Celery Task Queue (Redis broker)
      ├── Celery Worker → SMTP (emails)
      ├── Celery Worker → Telegram Bot API
      └── Celery Beat  → Periodic tasks (SLA checks, digests)
```
