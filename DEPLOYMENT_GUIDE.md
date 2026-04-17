# Посібник з розгортування EstateOS — Однодеплойне рішення для багатьох клієнтів

**Версія:** 2.0 — Multi-Tenant Single Deployment  
**Дата оновлення:** Квітень 2026  
**Технологічний стек:** Django 4.2 + Next.js 14 + PostgreSQL + Cloudflare R2 + Railway + Vercel

Цей посібник описує розгортування **однієї установки EstateOS**, яка одночасно обслуговує **всіх клієнтів** (організацій) через механізм організаційного розділення даних.

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
│         EstateOS Platform (Single Deploy)       │
│  Railway: estate-os.up.railway.app              │
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
CNAME zhk-sunny.estateos.com → estate-os.up.railway.app
```

або за допомогою wildcard (рекомендується):

```
CNAME *.estateos.com → estate-os.up.railway.app
```

**5. Frontend автоматично визначає Organization:**

Коли користувач заходить на `zhk-sunny.estateos.com`:
- Vercel frontend розпізнає поддомен
- API отримує `X-Organization-Slug: zhk-sunny`
- Дані завантажуються для цієї організації
- UI показує брендинг цієї організації

**6. Готово! Клієнт живе:** 🎉

- Dashboard: `https://zhk-sunny.estateos.com`
- API: `https://api.estateos.com` (з header `X-Organization-Slug: zhk-sunny`)

---

## 3. Railway (Backend + PostgreSQL)

### 3.1. Реєстрація та створення проекту

1. Перейдіть на [railway.app](https://railway.app)
2. **Sign up** через GitHub
3. **New Project** → **GitHub Repo** → виберіть `Django-Apartment-Management`
4. Виберіть гілку: **main**

### 3.2. Додавання PostgreSQL

У Railway Dashboard:

1. **New** → **Database** → **PostgreSQL**
2. Railway автоматично встановить `DATABASE_URL` у змінні

### 3.3. Environment Variables для Multi-Tenant

Натисніть на Django сервіс → **Variables** і добавте:

#### Обов'язкові для Production:

| Змінна | Значення | Опис |
|--------|----------|------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | Production settings |
| `DJANGO_DEBUG` | `False` | Ніколи True на production! |
| `DJANGO_SECRET_KEY` | `your-50-char-random-key` | Генерується один раз |
| `DJANGO_ALLOWED_HOSTS` | `*.estateos.com,api.estateos.com` | Всі поддомени |
| `SITE_NAME` | `EstateOS` | Platform назва |
| `TIME_ZONE` | `Europe/Kyiv` | Часовий пояс |

#### Email:

| Змінна | Значення |
|--------|----------|
| `DJANGO_EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | `your-email@gmail.com` |
| `EMAIL_HOST_PASSWORD` | `your-app-password` |
| `EMAIL_USE_TLS` | `True` |
| `DEFAULT_FROM_EMAIL` | `noreply@estateos.com` |

#### Google OAuth:

| Змінна | Значення |
|--------|----------|
| `GOOGLE_CLIENT_ID` | `your-client-id.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | `your-client-secret` |

#### Cloudflare R2 (Storage):

| Змінна | Значення |
|--------|----------|
| `USE_S3` | `True` |
| `AWS_ACCESS_KEY_ID` | Cloudflare R2 ключ |
| `AWS_SECRET_ACCESS_KEY` | Cloudflare R2 secret |
| `AWS_STORAGE_BUCKET_NAME` | `estate-os-media` |
| `AWS_S3_REGION_NAME` | `auto` |
| `AWS_S3_ENDPOINT_URL` | `https://<account-id>.r2.cloudflarestorage.com` |
| `AWS_S3_USE_SSL` | `True` |
| `AWS_QUERYSTRING_AUTH` | `False` |

#### CORS:

| Змінна | Значення |
|--------|----------|
| `CORS_ALLOWED_ORIGINS` | `https://*.estateos.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://*.estateos.com` |

### 3.4. Procfile

Створіть **Procfile** у корені проекту:

```
web: cd server && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --timeout 60
worker: cd server && celery -A config.celery_app worker --loglevel info
beat: cd server && celery -A config.celery_app beat --loglevel info
```

### 3.5. Перший Deploy

Railway автоматично запустить build. Коли готово:

```bash
# Підключіться через Railway CLI
railway connect

# Запустіть міграції
python manage.py migrate --no-input

# Завантажте статичні файли
python manage.py collectstatic --no-input

# Створіть SuperUser
python manage.py createsuperuser
# email: superadmin@estateos.com
```

### 3.6. Custom Domain для API

1. Django Service → **Settings → Domain**
2. **Add Domain:** `api.estateos.com`
3. Скопіюйте CNAME запис та додайте до Cloudflare

---

## 4. Cloudflare R2 (Storage для медіа)

### 4.1. Створення R2 Bucket

1. [dash.cloudflare.com](https://dash.cloudflare.com) → **R2 Object Storage**
2. **Create bucket** → назвіть `estate-os-media`
3. Регіон: **Auto**

### 4.2. API Tokens

1. **R2 → API Tokens** → **Create API token**
2. Дозволи: `Account > R2 > All buckets > Read and write`
3. Скопіюйте **Access Key ID** та **Secret Access Key**
4. Додайте у Railway Variables

### 4.3. Публічний доступ (опціонально)

Якщо потрібен публічний URL для медіа без auth:

1. **R2 → Buckets → estate-os-media → Settings**
2. Знайдіть **CORS** і добавте:

```json
{
  "AllowedOrigins": ["https://*.estateos.com"],
  "AllowedMethods": ["GET", "HEAD"],
  "AllowedHeaders": ["*"],
  "MaxAgeSeconds": 3600
}
```

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
| `NEXT_PUBLIC_API_URL` | `https://api.estateos.com` |
| `NEXT_PUBLIC_APP_NAME` | `EstateOS` |
| `NEXT_PUBLIC_ENVIRONMENT` | `production` |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | `your-client-id.apps.googleusercontent.com` |

### 5.5. Custom Domains

1. **Settings → Domains**
2. **Add Domain:** Додайте основний домен та поддомени для кожного клієнта
   - `estateos.com` → основний
   - `*.estateos.com` → поддомени для клієнтів (wildcard)

Vercel видаст CNAME для додавання до Cloudflare.

### 5.6. Deploy

1. **Deploy** на Vercel
2. Верifying domains займає 5-15 хвилин
3. SSL автоматично видається через Let's Encrypt

---

## 6. Cloudflare (DNS + SSL)

### 6.1. Додавання домену

1. [dash.cloudflare.com](https://dash.cloudflare.com) → **Add a site**
2. Введіть `estateos.com`
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
CNAME   api                estate-os.up.railway.app
```

#### Для Vercel (Frontend):

```
Type    Name               Content
CNAME   @                  cname.vercel-dns.com
CNAME   www                cname.vercel-dns.com
CNAME   *.estateos.com     cname.vercel-dns.com
```

#### Для інших поддоменів клієнтів:

```
CNAME   *.estateos.com     cname.vercel-dns.com
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

Заходіть на `https://api.estateos.com/django-admin/` з акаунтом SuperAdmin.

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
curl -H "Authorization: Bearer $TOKEN" https://api.estateos.com/api/v1/orgs/organizations/

# Створити організацію
curl -X POST https://api.estateos.com/api/v1/orgs/organizations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ЖК Новий",
    "slug": "zhk-new",
    "type": "housing_complex",
    "city": "Київ"
  }'

# Додати члена
curl -X POST https://api.estateos.com/api/v1/orgs/memberships/ \
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
7. ✅ Тестувати доступ: `https://zhk-name.estateos.com`

**Що отримує клієнт:**

- Dashboard на `https://zhk-name.estateos.com`
- API access через `https://api.estateos.com` з header `X-Organization-Slug: zhk-name`
- Приватний вход для директора
- Можливість приглашати інших користувачів

---

## 9. Моніторинг та обслуговування

### 9.1. Health Checks

**Backend:**
```bash
curl https://api.estateos.com/api/v1/schema/
# Очікуємо: 200 + OpenAPI schema JSON
```

**Frontend:**
```bash
curl https://estateos.com/
# Очікуємо: 200 + Next.js HTML
```

**Для конкретної організації:**
```bash
curl -H "X-Organization-Slug: zhk-sunny" https://api.estateos.com/api/v1/orgs/organizations/self/
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
CNAME custom-domain.com → api.estateos.com
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
