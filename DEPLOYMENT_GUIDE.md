# Посібник з розгортування ApartmentOS — Однодеплойне рішення для багатьох клієнтів

**Версія:** 2.0 — Multi-Tenant Single Deployment  
**Дата оновлення:** Квітень 2026  
**Технологічний стек:** Django 4.2 + Next.js 14 + PostgreSQL + Cloudflare R2 + Railway + Vercel

Цей посібник описує розгортування **однієї установки ApartmentOS**, яка одночасно обслуговує **всіх клієнтів** (організацій) через механізм організаційного розділення даних.

---

## Зміст

1. [Архітектура Multi-Tenant](#1-архітектура-multi-tenant)
2. [Додавання нового клієнта (без нового деплою!)](#2-додавання-нового-клієнта-без-нового-деплою)
3. [Railway (Backend + PostgreSQL)](#3-railway-backend--postgresql)
4. [Cloudflare R2 (Storage для медіа)](#4-cloudflare-r2-storage-для-медіа)
5. [Vercel (Next.js Frontend)](#5-vercel-nextjs-frontend)
6. [Cloudflare (DNS + SSL)](#6-cloudflare-dns--ssl)
7. [GitHub Actions (CI/CD автоматизація)](#7-github-actions-cicd-автоматизація)
8. [Керування клієнтами (SuperAdmin)](#8-керування-клієнтами-superadmin)
9. [Моніторинг та обслуговування](#9-моніторинг-та-обслуговування)

---

## 1. Архітектура Multi-Tenant

### Головна різниця від старої версії:

**ДО (per-client deployment):**
```
Клієнт A → Railway Deploy A → PostgreSQL A
Клієнт B → Railway Deploy B → PostgreSQL B
Клієнт C → Railway Deploy C → PostgreSQL C
❌ Три окремих деплои, три різні URL, trois базі даних
```

**ТЕПЕР (single deployment):**
```
┌─────────────────────────────────────────────────┐
│         ApartmentOS Platform (Single Deploy)       │
│  Railway: apartment-os.up.railway.app              │
│  PostgreSQL: одна база + schema розділення       │
└─────────────────────────────────────────────────┘
          ↓              ↓              ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Клієнт A     │  │ Клієнт B     │  │ Клієнт C     │
│ org: "a-sk"  │  │ org: "b-park"│  │ org: "c-city"│
│ zhk-a.com    │  │ zhk-b.com    │  │ zhk-c.com    │
└──────────────┘  └──────────────┘  └──────────────┘
     ↓                    ↓                    ↓
   (одна базу даних PostgreSQL)
   (Організація визначає дані в базі)
✅ Один деплой, один database, багато клієнтів
```

### Як працює організаційне розділення:

1. **X-Organization-Slug Header** — API запити передають: `X-Organization-Slug: a-sk`
2. **Subdomain Detection** — `zhk-a.com` → автоматично визначає `org: a-sk`
3. **Database Scoping** — модели Buildings, Issues, Posts мають FK на `Organization`
4. **Frontend Context** — Next.js знає поточну організацію через URL/header

### Модели з підтримкою Organizations:

✅ **Org-Scoped (безпечні для multi-tenant):**
- Buildings, Entrances, Units
- Issues, VehiclePass, Posts, News
- Notifications (для користувачів у організації)

⚠️ **Частково Scoped (потребують уваги):**
- Categories (Issues) — глобальна, але може бути розширена
- NewsCategory — глобальна

❌ **Not Scoped (потребують міграції):**
- SiteSettings (поточно singleton = pk=1)
- Ratings, Reports
- ContactPersons

---

## 2. Додавання нового клієнта (без нового деплою!)

### Процес для SuperAdmin

Замість того щоб розгортувати новий код, просто:

#### Кроки:

**1. Створити Organization (через API або Django Admin):**

```bash
POST /api/v1/orgs/organizations/
Content-Type: application/json

{
  "name": "ЖК Сонячний",
  "slug": "zhk-sunny",
  "type": "housing_complex",
  "city": "Київ",
  "address": "вул. Тестова, 1",
  "email": "admin@zhk-sunny.com",
  "phone": "+380671234567"
}

# Відповідь:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "slug": "zhk-sunny",
  "name": "ЖК Сонячний",
  ...
}
```

**2. Додати Director (керівника) організації:**

```bash
POST /api/v1/orgs/memberships/
Content-Type: application/json

{
  "user_email": "director@zhk-sunny.com",
  "organization_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "director"
}
```

(користувач буде запрошений через email, потім може логінутися)

**3. Налаштувати брендинг (SiteSettings для організації):**

```bash
PATCH /api/v1/orgs/organizations/550e8400-e29b-41d4-a716-446655440000/site-settings/
Content-Type: application/json

{
  "platform_name": "ЖК Сонячний",
  "primary_color": "#3D7A8A",
  "logo_url": "https://cdn.example.com/logos/zhk-sunny.png",
  "support_email": "support@zhk-sunny.com",
  "support_phone": "+380671234567"
}
```

**4. Налаштувати DNS (додати CNAME для нового домену):**

```
CNAME zhk-sunny.apartmentos.org → apartment-os.up.railway.app
```

або за допомогою wildcard (рекомендується):

```
CNAME *.apartmentos.org → apartment-os.up.railway.app
```

**5. Frontend автоматично визначає Organization:**

Коли користувач заходить на `zhk-sunny.apartmentos.org`:
- Vercel frontend розпізнає поддомен
- API отримує `X-Organization-Slug: zhk-sunny`
- Дані завантажуються для цієї організації
- UI показує брендинг цієї організації

**6. Готово! Клієнт живе:** 🎉

- Dashboard: `https://zhk-sunny.apartmentos.org`
- API: `https://api.apartmentos.org` (з header `X-Organization-Slug: zhk-sunny`)

---

## 3. Railway (Backend + PostgreSQL)

### 3.1. Реєстрація та створення проекту

1. Перейдіть на [railway.app](https://railway.app) та **Sign up** через GitHub
2. **New Project** → **GitHub Repo** → виберіть `LukaBrazi/Apartment-Management`
3. Railway створить сервіс **Apartment-Management** і прив'яже його до гілки **main** (або **production**)
4. Поки що деплой впаде — це нормально, потрібно ще налаштувати базу та змінні

### 3.2. Додавання PostgreSQL (покроково)

Ця інструкція базується на інтерфейсі Railway станом на квітень 2026 (project canvas UI).

**Крок 1.** Відкрийте свій проєкт на Railway (наприклад `cooperative-stillness`)

**Крок 2.** У верхньому правому куті натисніть кнопку **"+ Add"**

**Крок 3.** У меню що з'явиться оберіть **"Database"**

**Крок 4.** У списку баз даних натисніть **"PostgreSQL"**

**Крок 5.** Railway автоматично:
- Створить PostgreSQL інстанс
- Виділить volume для даних (`postgres-volume`)
- Згенерує 13 змінних підключення (`DATABASE_URL`, `DATABASE_PUBLIC_URL`, `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` та інші)
- Статус зміниться на **Online** протягом 10-30 секунд

**Крок 6.** Прив'яжіть DATABASE_URL до сервісу Apartment-Management:
1. Натисніть на сервіс **Apartment-Management** на канвасі
2. Перейдіть на вкладку **Variables**
3. Railway покаже підказку: "Trying to connect a database? **Add Variable**" — натисніть на **Add Variable**
4. У випадаючому списку виберіть **DATABASE_URL** (з іконкою Postgres)
5. Railway автоматично заповнить ім'я `DATABASE_URL` і значення `${{Postgres.DATABASE_URL}}`
6. Натисніть **Add** (кнопка з галочкою)

Тепер ваш Django сервіс має доступ до бази через змінну `DATABASE_URL`.

### 3.3. Налаштування Source (Root Directory)

Оскільки Django бекенд знаходиться у папці `server/` (а не в корені репозиторію), потрібно вказати Railway де шукати код:

1. Натисніть на сервіс **Apartment-Management** → вкладка **Settings**
2. У секції **Source** знайдіть посилання **"Add Root Directory"**
3. У поле введіть: `server`
4. Натисніть галочку (✓) щоб зберегти

### 3.4. Налаштування Start Command

1. У **Settings** → секція **Deploy** → **Custom Start Command**
2. Натисніть **"+ Start Command"**
3. Введіть:

```
python manage.py migrate && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

4. Натисніть галочку (✓) щоб зберегти

Ця команда при кожному деплої: запускає міграції БД → збирає статичні файли → стартує gunicorn сервер.

### 3.5. Додавання Redis (для Celery та Cache)

Аналогічно до PostgreSQL:

1. **"+ Add"** → **"Database"** → **"Redis"**
2. Після створення, перейдіть до **Apartment-Management** → **Variables**
3. Додайте змінну **REDIS_URL** з посиланням на Redis сервіс: `${{Redis.REDIS_URL}}`

### 3.6. Environment Variables (обов'язкові)

Натисніть **Apartment-Management** → **Variables** → **Raw Editor** для швидкого додавання всіх змінних.

Повний набір змінних відповідно до `config/settings/production.py` (12 штук):

```env
# === Django Core ===
DATABASE_URL="${{Postgres.DATABASE_URL}}"
DJANGO_SETTINGS_MODULE="config.settings.production"
DJANGO_SECRET_KEY="<згенеруйте: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'>"
DJANGO_ALLOWED_HOSTS=".railway.app,.up.railway.app"
CSRF_TRUSTED_ORIGINS="https://*.railway.app,https://*.up.railway.app"
CORS_ALLOWED_ORIGINS="https://*.up.railway.app,https://*.railway.app"

# === Redis (Cache + Celery) ===
REDIS_URL="${{Redis.REDIS_URL}}"

# === Cloudflare R2 Storage ===
R2_BUCKET_NAME="skandi-apartments-media"
R2_ENDPOINT_URL="https://206285afe5c77ccfcbbd7e6499b0c32e.r2.cloudflarestorage.com"
R2_ACCESS_KEY_ID="<ваш R2 Access Key ID з Cloudflare>"
R2_SECRET_ACCESS_KEY="<ваш R2 Secret Access Key з Cloudflare>"
R2_PUBLIC_URL="https://pub-5f7e0280570b4983b9e1f7f2cfdf1e00.r2.dev"

# === Email (SMTP) — ОБОВ'ЯЗКОВО для деплою ===
EMAIL_HOST="smtp.gmail.com"
EMAIL_HOST_USER="your-email@gmail.com"
EMAIL_HOST_PASSWORD="your-app-password"
```

> **⚠️ Важливо:** Без EMAIL_* змінних деплой впаде, тому що `production.py` вимагає їх при імпорті. Якщо SMTP ще не готовий, можна тимчасово закоментувати email блок у `config/settings/production.py`.

Натисніть **Update Variables** щоб зберегти все одразу.

Додатково Railway автоматично додає 7 системних змінних (`PORT`, `RAILWAY_ENVIRONMENT`, `RAILWAY_PUBLIC_DOMAIN` тощо) — їх не треба вказувати вручну.

### 3.7. Перший Deploy

Після налаштування всіх змінних:

1. Зверху на канвасі натисніть **"Deploy"** (фіолетова кнопка)
2. Railway:
   - Клонує репо з GitHub
   - Переходить у папку `server/` (Root Directory)
   - Автоматично знаходить `requirements.txt` і встановлює залежності (Railpack builder)
   - Виконує Start Command: migrate → collectstatic → gunicorn
3. Слідкуйте за процесом у вкладці **Deployments** → натисніть на деплой щоб бачити логи

Якщо деплой впав — дивіться логи. Типові проблеми:
- Відсутня змінна → додайте у Variables
- Помилка імпорту → перевірте `requirements.txt` у папці `server/`
- Помилка міграції → перевірте що PostgreSQL Online

### 3.8. Створення SuperUser

Після успішного деплою створіть адміністратора через Railway CLI:

```bash
# Встановіть Railway CLI
npm install -g @railway/cli

# Авторизуйтесь
railway login

# Підключіться до проєкту
railway link

# Створіть superuser
railway run -s Apartment-Management python manage.py createsuperuser
# Введіть: email, пароль
```

Або через Railway Dashboard → сервіс → вкладка **Settings** → **Railway Shell** (якщо доступно).

### 3.9. Custom Domain для API

1. Натисніть на **Apartment-Management** → **Settings** → секція **Networking**
2. **Generate Domain** — Railway видасть домен типу `apartment-management-production-xxxx.up.railway.app`
3. Для кастомного домену: **"+ Custom Domain"** → введіть `api.apartmentos.org`
4. Railway покаже CNAME запис — додайте його до Cloudflare DNS

### 3.10. Структура проєкту на Railway (фінальна)

Після всіх налаштувань на канвасі Railway повинно бути:

```
Railway Project: cooperative-stillness
Environment: production

┌─────────────────────────────┐     ┌──────────────┐
│  Apartment-Management       │────→│   Postgres   │
│  (Django Backend)           │     │   (Online)   │
│  Root: server/              │     │   + volume   │
│  12 Service Variables:      │     └──────────────┘
│   - DATABASE_URL            │
│   - DJANGO_SETTINGS_MODULE  │     ┌──────────────┐
│   - DJANGO_SECRET_KEY       │────→│    Redis     │
│   - DJANGO_ALLOWED_HOSTS    │     │   (Online)   │
│   - CSRF_TRUSTED_ORIGINS    │     │   + volume   │
│   - CORS_ALLOWED_ORIGINS    │     └──────────────┘
│   - REDIS_URL               │
│   - R2_BUCKET_NAME          │     ┌──────────────┐
│   - R2_ENDPOINT_URL         │────→│ Cloudflare   │
│   - R2_ACCESS_KEY_ID        │     │ R2 Storage   │
│   - R2_SECRET_ACCESS_KEY    │     │ (external)   │
│   - R2_PUBLIC_URL           │     └──────────────┘
│  + 7 Railway auto-variables │
└─────────────────────────────┘
         ↓
   *.up.railway.app (Public URL)
```

---

## 4. Cloudflare R2 (Storage для медіа)

Cloudflare R2 — S3-сумісне об'єктне сховище з безкоштовним тарифом (10 GB, 1M Class A ops, 10M Class B ops на місяць, без egress fees).

### 4.1. Активація R2

1. [dash.cloudflare.com](https://dash.cloudflare.com) → ліва панель → **Storage & databases** → **R2 Object Storage**
2. Натисніть **Activate R2** (або **Get Started**)
3. Cloudflare попросить прив'язати картку — R2 має **Free tier** ($0/міс), картка потрібна тільки як гарантія
4. Після активації ви потрапите на сторінку R2 Overview

### 4.2. Створення Bucket

1. Натисніть **Create bucket**
2. **Bucket name:** `skandi-apartments-media` (або ваша назва, наприклад `apartmentos-media`)
3. **Location:** оберіть **Eastern Europe (EEUR)** — найближче до України
4. Натисніть **Create bucket**

Після створення ви побачите bucket з параметрами:
- **S3 API:** `https://<ACCOUNT_ID>.r2.cloudflarestorage.com/skandi-apartments-media`
- **Location:** Eastern Europe (EEUR)

### 4.3. Увімкнення публічного доступу (Public Development URL)

Django `collectstatic` збирає статичні файли в R2, і вони повинні бути доступні по URL.

1. Відкрийте bucket → вкладка **Settings**
2. У лівому меню натисніть **Public Development URL**
3. Натисніть **Enable** → підтвердіть натиснувши **Allow**
4. Cloudflare згенерує публічний URL: `https://pub-<hash>.r2.dev`

> **Наш URL:** `https://pub-5f7e0280570b4983b9e1f7f2cfdf1e00.r2.dev`

Це значення буде використане як `R2_PUBLIC_URL` у Railway.

> **Для продакшну** рекомендується замість Dev URL використовувати **Custom Domain** (секція Custom Domains у тих самих Settings) — це дає контроль над кешуванням і красивий URL.

### 4.4. Створення API Token (для Django)

Django використовує `django-storages` з `S3Boto3Storage` для завантаження файлів у R2. Для цього потрібен API Token.

1. Перейдіть: **R2 Object Storage** → **API Tokens** (або пряме посилання: `dash.cloudflare.com/<ACCOUNT_ID>/r2/api-tokens`)
2. Натисніть **Create Account API Token**
3. Заповніть форму:
   - **Token name:** `skandi-railway-production` (або інше зрозуміле ім'я)
   - **Permissions:** оберіть **Object Read & Write** (НЕ Admin — Django не потребує адмін-доступу)
   - **Specify bucket(s):** оберіть **Apply to specific buckets only** → виберіть ваш bucket (`skandi-apartments-media`)
   - **TTL:** залиште **Forever** (або встановіть термін дії)
   - **Client IP Address Filtering:** залиште порожнім
4. Натисніть **Create Account API Token**

5. **ВАЖЛИВО!** На наступній сторінці скопіюйте та збережіть:
   - **Access Key ID** → це буде `R2_ACCESS_KEY_ID`
   - **Secret Access Key** → це буде `R2_SECRET_ACCESS_KEY`
   - **Endpoint URL** → `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` → це `R2_ENDPOINT_URL`

> **⚠️ Secret Access Key показується тільки один раз!** Якщо втратите — доведеться створювати новий токен.

### 4.5. CORS Policy (для фронтенду)

Якщо фронтенд завантажує файли напряму в R2 або показує медіа:

1. Bucket → **Settings** → **CORS Policy**
2. Додайте правило:

```json
[
  {
    "AllowedOrigins": ["https://*.railway.app", "https://*.up.railway.app"],
    "AllowedMethods": ["GET", "HEAD", "PUT"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3600
  }
]
```

### 4.6. Підсумок R2 змінних для Railway

| Змінна | Значення | Де взяти |
|--------|----------|----------|
| `R2_BUCKET_NAME` | `skandi-apartments-media` | Ім'я bucket при створенні |
| `R2_ENDPOINT_URL` | `https://206285afe5c77ccfcbbd7e6499b0c32e.r2.cloudflarestorage.com` | Сторінка Success після створення токена, або R2 Overview |
| `R2_ACCESS_KEY_ID` | `96250541366b7ba5...` | Сторінка Success (показується один раз!) |
| `R2_SECRET_ACCESS_KEY` | `14338813cb4a2ca3...` | Сторінка Success (показується один раз!) |
| `R2_PUBLIC_URL` | `https://pub-5f7e0280570b4983b9e1f7f2cfdf1e00.r2.dev` | Bucket Settings → Public Development URL |

---

## 5. Vercel (Next.js Frontend)

### 5.1. Реєстрація на Vercel

1. [vercel.com](https://vercel.com) → **Sign Up** через GitHub
2. Поєднайте аккаунт

### 5.2. Імпорт Next.js проекту

1. **New Project** → **Import Git Repository**
2. Виберіть `Django-Apartment-Management`
3. **Import**

### 5.3. Build Settings

На **Project Settings**:

- **Framework:** Next.js
- **Build Command:** `cd client && npm run build`
- **Output Directory:** `client/.next`
- **Node.js Version:** 20.x

### 5.4. Environment Variables

На **Settings → Environment Variables**:

| Змінна | Значення |
|--------|----------|
| `NEXT_PUBLIC_API_URL` | `https://api.apartmentos.org` |
| `NEXT_PUBLIC_APP_NAME` | `ApartmentOS` |
| `NEXT_PUBLIC_ENVIRONMENT` | `production` |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | `your-client-id.apps.googleusercontent.com` |

### 5.5. Custom Domains

1. **Settings → Domains**
2. **Add Domain:** Додайте основний домен та поддомени для кожного клієнта
   - `apartmentos.org` → основний
   - `*.apartmentos.org` → поддомени для клієнтів (wildcard)

Vercel видаст CNAME для додавання до Cloudflare.

### 5.6. Deploy

1. **Deploy** на Vercel
2. Верifying domains займає 5-15 хвилин
3. SSL автоматично видається через Let's Encrypt

---

## 6. Cloudflare (DNS + SSL)

### 6.1. Додавання домену

1. [dash.cloudflare.com](https://dash.cloudflare.com) → **Add a site**
2. Введіть `apartmentos.org`
3. Виберіть **Free plan**

### 6.2. Nameservers

Cloudflare покаже nameservers. Оновіть їх у реєстрара домену (де ви купили домен):

```
ns1.cloudflare.com
ns2.cloudflare.com
```

Пропагація: 24-48 годин.

### 6.3. DNS Записи

На **Cloudflare → Domain → DNS**:

#### Для Railway (Backend API):

```
Type    Name               Content
CNAME   api                apartment-os.up.railway.app
```

#### Для Vercel (Frontend):

```
Type    Name               Content
CNAME   @                  cname.vercel-dns.com
CNAME   www                cname.vercel-dns.com
CNAME   *.apartmentos.org     cname.vercel-dns.com
```

#### Для інших поддоменів клієнтів:

```
CNAME   *.apartmentos.org     cname.vercel-dns.com
```

(Wildcard CNAME автоматично покриває всі нові поддомени клієнтів!)

### 6.4. SSL/HTTPS

На **SSL/TLS**:

1. **Mode:** Full (strict)
2. **Always Use HTTPS:** ON
3. **Minimum TLS Version:** 1.2

### 6.5. Security

На **Security**:

- **Security Level:** Medium
- **DDoS Protection:** Included
- **WAF:** Enabled (OWASP Top 10)

---

## 7. GitHub Actions (CI/CD автоматизація)

### 7.1. GitHub Secrets

На **Settings → Secrets and variables → Actions**, добавте:

| Секрет | Значення |
|--------|----------|
| `RAILWAY_API_TOKEN` | З [railway.app/account/tokens](https://railway.app/account/tokens) |
| `RAILWAY_PROJECT_ID` | ID Railway проекту |
| `VERCEL_TOKEN` | З [vercel.com/account/tokens](https://vercel.com/account/tokens) |
| `VERCEL_PROJECT_ID` | ID Vercel проекту |
| `VERCEL_ORG_ID` | Vercel Organization ID |

### 7.2. GitHub Actions Workflow

Створіть `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches:
      - main

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r server/requirements/base.txt
          pip install pytest pytest-django pytest-cov
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://test_user:test_password@localhost:5432/test_db
          DJANGO_SETTINGS_MODULE: config.settings.ci
        run: |
          cd server && pytest -v

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Railway
        env:
          RAILWAY_API_TOKEN: ${{ secrets.RAILWAY_API_TOKEN }}
          RAILWAY_PROJECT_ID: ${{ secrets.RAILWAY_PROJECT_ID }}
        run: |
          npm install -g @railway/cli
          railway up --service django-server
      
      - name: Run migrations
        env:
          RAILWAY_API_TOKEN: ${{ secrets.RAILWAY_API_TOKEN }}
          RAILWAY_PROJECT_ID: ${{ secrets.RAILWAY_PROJECT_ID }}
        run: |
          railway run python manage.py migrate --no-input

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Vercel
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
        run: |
          npm install -g vercel
          vercel deploy --prod --token ${{ secrets.VERCEL_TOKEN }} --cwd client
```

---

## 8. Керування клієнтами (SuperAdmin)

### 8.1. Django Admin для SuperAdmin

Заходіть на `https://api.apartmentos.org/django-admin/` з акаунтом SuperAdmin.

#### Керування Organizations:

1. **Organizations → Organizations List**
2. **Add Organization:**
   - Name: ЖК Сонячний
   - Slug: zhk-sunny
   - Type: housing_complex
   - Owner: (select)
   - Features: {} (можна залишити пусто)

#### Додавання членів до організації:

1. **Organizations → Memberships**
2. **Add Membership:**
   - User: (select або create)
   - Organization: (select)
   - Role: director / admin / staff / resident
   - Is Active: ☑

#### Site Settings для організації:

1. **Site Settings → Site Settings**
2. Редагуйте брендинг (поточно singleton, буде розширено)

### 8.2. API для SuperAdmin

Альтернативно можна використовувати API:

```bash
# Список всіх організацій
curl -H "Authorization: Bearer $TOKEN" https://api.apartmentos.org/api/v1/orgs/organizations/

# Створити організацію
curl -X POST https://api.apartmentos.org/api/v1/orgs/organizations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ЖК Новий",
    "slug": "zhk-new",
    "type": "housing_complex",
    "city": "Київ"
  }'

# Додати члена
curl -X POST https://api.apartmentos.org/api/v1/orgs/memberships/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "director@zhk.com",
    "organization": 1,
    "role": "director"
  }'
```

### 8.3. Процес Onboarding Нового Клієнта

**Кроки AdministratorFor SuperAdmin:**

1. ✅ Отримали запит від нового клієнта
2. ✅ Створити Organization у Django Admin / API
3. ✅ Пригласити Director (відправиться email)
4. ✅ Налаштувати SiteSettings (брендинг, контакти)
5. ✅ Додати DNS CNAME запис для поддомену в Cloudflare
6. ✅ Чекати пропагації DNS (5-15 хвилин)
7. ✅ Тестувати доступ: `https://zhk-name.apartmentos.org`

**Що отримує клієнт:**

- Dashboard на `https://zhk-name.apartmentos.org`
- API access через `https://api.apartmentos.org` з header `X-Organization-Slug: zhk-name`
- Приватний вход для директора
- Можливість приглашати інших користувачів

---

## 9. Моніторинг та обслуговування

### 9.1. Health Checks

> **Налаштування Railway healthcheck — див. покрокову інструкцію [docs/RAILWAY_SETUP.md](docs/RAILWAY_SETUP.md).**
> Це окремий gotcha для multi-service Railway деплоїв: Celery Worker і Beat
> мають мати **порожній** healthcheck path, інакше деплой падає.

**Backend (perdiously DB + Redis ping):**
```bash
curl https://api.apartmentos.org/api/v1/health/
# 200 OK: {"status":"healthy","checks":{"db":"ok","cache":"ok"}}
# 503:    {"status":"unhealthy","checks":{"db":"fail","cache":"ok"}}
```

**Frontend:**
```bash
curl https://apartmentos.org/
# Очікуємо: 200 + Next.js HTML
```

**Для конкретної організації:**
```bash
curl -H "X-Organization-Slug: zhk-sunny" https://api.apartmentos.org/api/v1/orgs/organizations/self/
# Показує дані організації
```

### 9.2. Логування та Debug

На Railway Dashboard:

1. **Deployments** → поточний → **Logs**
2. Фільтруйте за:
   - `ERROR` — помилки
   - `WARNING` — попередження
   - `organization_slug` — конкретну організацію

### 9.3. Database Management

```bash
# Підключіться до PostgreSQL через Railway
railway connect postgresql

# Перегляд організацій
SELECT id, name, slug, is_active FROM organizations_organization;

# Очистити дані організації
DELETE FROM apartments_building WHERE organization_id = <id>;
DELETE FROM issues_issue WHERE organization_id = <id>;
```

### 9.4. Масштабування

Якщо кількість клієнтів растає:

1. **Railway:** додайте більше workers
   - **Settings → Instances** → збільшити кількість
   - **CPU/RAM:** збільшити за потребою

2. **PostgreSQL:** додайте читаючі репліки
   - Railway auto-handles за Hobby+ plan

3. **Vercel:** автоматично масштабується

### 9.5. Бекап Database

Railway автоматично робить бекапи. Щоб скачати:

1. **PostgreSQL Service → Settings**
2. **Backups** → знайдіть потрібний та скачайте

Або вручну:
```bash
railway connect postgresql
pg_dump > backup.sql
```

---

## Часто задавані питання

### Q: Скільки клієнтів може обслуговувати один деплой?

**A:** 1000+ на сучасному Railway infrastructure. PostgreSQL буде вузьким місцем першим.

### Q: Як міцліти дані одного клієнта від іншого?

**A:** Всі моделі мають `organization` FK. API views автоматично фільтрують за `X-Organization-Slug` header.

### Q: Що якщо у мене є клієнти на власних доменах (не поддомени)?

**A:** Cloudflare може перенаправляти будь-який домен:
```
CNAME custom-domain.com → api.apartmentos.org
```

Додайте домен до Cloudflare та налаштуйте перенаправлення.

### Q: Чи можна перенести клієнта з одного деплою на інший?

**A:** Так, через SQL export/import of organization data.

```bash
# Export
psql $DATABASE_URL -c "SELECT * FROM organizations_organization WHERE slug='zhk-old';" > export.sql

# Import
psql $NEW_DATABASE_URL < export.sql
```

---

**Готово! Ваша платформа обслуговує всіх клієнтів з одного місця.** 🚀
