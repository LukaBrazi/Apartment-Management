# Railway Setup — ApartmentOS

> Покрокова інструкція як налаштувати/виправити Railway-деплой ApartmentOS.
> Якщо щось пішло не так — спочатку шукай свою помилку в розділі **Troubleshooting** у кінці.

ApartmentOS на Railway — це **3 окремих сервіси** з одного git-репо:

| # | Сервіс | Що робить | Має HTTP? |
|---|---|---|---|
| 1 | **Web** | Django + Gunicorn — обробляє API запити, virtual host = `apartmentos.org` | ✅ Так |
| 2 | **Celery Worker** | Виконує фонові задачі (email, Telegram нотифікації, seed_demo_reset) | ❌ Ні |
| 3 | **Celery Beat** | Планувальник — кладе задачі у чергу за розкладом | ❌ Ні |

PostgreSQL і Redis Railway надає як окремі **plugins** (managed services).

---

## 🚨 Найчастіша помилка — Healthcheck падає на Celery

**Симптом у Railway logs:**
```
==================== Starting Healthcheck ====================
Path: /api/v1/health/
Attempt #1 failed with service unavailable.
1/1 replicas never became healthy!
Healthcheck failed!
```

**Причина:** Celery Worker і Celery Beat **не мають HTTP сервера**. Якщо Railway спробує probe `/api/v1/health/` на них — нічого не отримає.

**Виправлення:** для Celery сервісів `Healthcheck Path` **має бути порожнім**.

Як налаштувати — нижче.

---

## Початкова настройка (тільки 1 раз для нового Railway проекту)

### Крок 1 — Створи проект і додай PostgreSQL + Redis

1. Railway dashboard → **New Project** → **Deploy from GitHub repo** → обери цей репо
2. Після першого деплою → **+ New** → **Database** → **PostgreSQL** → Add
3. **+ New** → **Database** → **Redis** → Add
4. Railway автоматично створить env vars `DATABASE_URL` і `REDIS_URL` у твоєму web-сервісі. Перевір це в `Settings → Variables`.

### Крок 2 — Налаштуй Web сервіс (вже створений автоматично)

Відкрий web-сервіс у dashboard:

#### 2.1. Settings → Variables (env vars)

Скопіюй з шаблону. Обов'язкові:

```
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<згенеруй: python -c "import secrets; print(secrets.token_urlsafe(64))">
DJANGO_ALLOWED_HOSTS=apartmentos.org,*.up.railway.app
CORS_ALLOWED_ORIGINS=https://apartmentos.org,https://www.apartmentos.org
ENVIRONMENT=production
DJANGO_ADMIN_URL=secret-admin-path/    # пройди генератор для шляху
DEMO_PASSWORD=<згенеруй пароль>
TELEGRAM_BOT_ENCRYPTION_KEYS=<Fernet key — generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
EMAIL_HOST=<твій SMTP>
EMAIL_HOST_USER=<>
EMAIL_HOST_PASSWORD=<>
DEFAULT_FROM_EMAIL=noreply@apartmentos.org

# GDPR (PR-5) — за замовчуванням 1.0
TOS_VERSION=1.0
PRIVACY_VERSION=1.0
```

#### 2.2. Settings → Deploy

```
Healthcheck Path:    /api/v1/health/
Healthcheck Timeout: 30
```

⚠️ Це **обов'язково** для Web. Без цього Railway не знатиме чи дошлюється деплой.

#### 2.3. Settings → Networking

- **Generate Domain** (Railway-роутер) — для тесту
- **Custom Domain** → `apartmentos.org` → Railway покаже DNS records
- У Cloudflare/іншому DNS постав ці records

### Крок 3 — Створи Celery Worker сервіс

1. У тому ж Railway проекті → **+ New** → **GitHub Repo** → **Empty Service** → обери **той самий репо**
2. Назви сервіс: `celery-worker`
3. Settings → Source → Branch: `main`
4. Settings → Variables → **скопіюй ВСІ env vars з Web сервісу** (можна через `Raw Editor` для масового вставлення)
5. Settings → Deploy:

```
Custom Start Command: celery -A config.celery_app worker --loglevel=info --concurrency=1
Healthcheck Path:     ⚠️ ЗАЛИШ ПОРОЖНІМ
Healthcheck Timeout:  ⚠️ ЗАЛИШ ПОРОЖНІМ
Replicas:             1
```

### Крок 4 — Створи Celery Beat сервіс

Те саме що Worker, але:
- Назва: `celery-beat`
- **Custom Start Command**:
  ```
  celery -A config.celery_app beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
  ```
- **Healthcheck Path: ⚠️ ЗАЛИШ ПОРОЖНІМ**
- **Healthcheck Timeout: ⚠️ ЗАЛИШ ПОРОЖНІМ**
- **Replicas: рівно 1** (більше — schedule дублюватиметься)

### Крок 5 — Перший міграційний прогон

Після першого успішного деплою:

```
Web service → Settings → Deploy → Custom Start Command (тимчасово):
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

Стандартна start command вже виконує `migrate` через `release` команду в `Dockerfile`. Якщо ні — зроби `Web service → Logs → Run Command → python manage.py migrate`.

### Крок 6 — Створи superuser

```
Web service → Logs → Run Command:
python manage.py createsuperuser
```

Введи email + password.

### Крок 7 — Завантаж demo дані (опційно)

```
Web service → Logs → Run Command:
python manage.py seed_demo --passwords-from-env
```

---

## Чеклист post-deploy після кожного push у main

1. **Web service deploy** — green ✅
2. `curl https://apartmentos.org/api/v1/health/` → `{"status":"healthy",...}`
3. **Celery worker deploy** — green ✅ (TCP probe, не HTTP)
4. **Celery beat deploy** — green ✅ (TCP probe)
5. Перевір що CELERY_BEAT_SCHEDULE задачі виконуються — Logs у worker сервісі мають показувати `Task ... succeeded`

---

## Troubleshooting

### "Attempt #N failed with service unavailable" на Celery worker/beat

**Причина:** хтось налаштував `Healthcheck Path` для цих сервісів.

**Виправлення:**
1. Railway dashboard → відкрий проблемний сервіс
2. Settings → Deploy → знайди **Healthcheck Path**
3. Очисти поле → **Save**
4. Settings → Deployments → **Redeploy**

### "Attempt #N failed with service unavailable" на Web

Декілька можливих причин:

**Причина 1 — DJANGO_ALLOWED_HOSTS не містить Railway internal hostname.**
Симптом у logs: `DisallowedHost: Invalid HTTP_HOST header`.
Fix: додай `*.up.railway.app` до `DJANGO_ALLOWED_HOSTS`.

**Причина 2 — SSL redirect зрізає probe.**
Перевір `server/config/settings/production.py` — там має бути:
```python
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/?$"]
```
Якщо нема — це регрес з PR-7 hotfix. Поверни цей рядок.

**Причина 3 — DB або Redis недоступні.**
Перевір що `DATABASE_URL` і `REDIS_URL` у Variables не порожні. Перевір що PostgreSQL і Redis services запущені у тому ж проекті.

### "ImproperlyConfigured: DJANGO_SECRET_KEY"

Не задано env var `DJANGO_SECRET_KEY`. Згенеруй і додай:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Celery worker запускається, але задачі не виконуються

1. Перевір що `CELERY_BROKER_URL` у Worker == `REDIS_URL` Web-сервіса
2. Перевір Beat сервіс — він має створити schedule. Logs у Beat показують `Sending due task ...`
3. Якщо Beat не запущений — задачі ніхто не кидатиме у чергу

### Migration не зробилась

```
Web service → Logs → Run Command → python manage.py migrate
```

Або переконайся що `Dockerfile` має `release` step з `python manage.py migrate`.

---

## Як НЕ зламати цей setup в майбутньому

🚫 **НЕ додавай `healthcheckPath` у root `railway.toml`** — він застосується до всіх сервісів і поламає Celery deploys. Налаштовуй per-service у dashboard.

🚫 **НЕ копіюй start command з `compose/` файлів** — там Docker-Compose specifics, які не працюють на Railway.

🚫 **НЕ роби Beat replicas > 1** — schedule буде дублюватись (одна задача виконається N разів).

✅ **Завжди тримай env vars synchronized** між Web і Celery сервісами — якщо додаєш нову env var у Web, додай у Worker і Beat.

✅ **Бекапи** — Railway managed Postgres робить snapshots автоматично (Hobby+ plan). Перевір **Settings → Database → Backups**.

✅ **Перед merge у main** — переглянь diff `railway.toml`. Якщо хтось додав `healthcheckPath` — виріж і обговори.

---

## Корисні команди в Railway Logs

```bash
# Django shell
python manage.py shell

# Перевірити що Telegram-бот працює
python manage.py shell -c "from apps.notifications.models import OrganizationBot; print([b.bot_username for b in OrganizationBot.objects.all()])"

# Чистка demo даних (тільки якщо ENVIRONMENT != production АБО ALLOW_DEMO_RESET=1)
python manage.py seed_demo --reset --passwords-from-env

# Trigger Celery task вручну
python manage.py shell -c "from apps.common.tasks import seed_demo_reset_task; seed_demo_reset_task.delay()"
```

---

## Production Logs — JSON (PR-8)

Починаючи з PR-8 production-логи Django у Railway пишуться як
структурований JSON (одне повідомлення = один рядок з полями
`timestamp`, `level`, `logger`, `message`, `module`, `funcName`,
`lineno`).

Це робиться через override LOGGING у `server/config/settings/production.py`
з форматтером `pythonjsonlogger.jsonlogger.JsonFormatter`. Dev / test
залишаються з plain-text формат — читати у термінал зручніше.

### Як читати ці логи

```bash
# Сирий JSON
railway logs

# Грепай по рівню
railway logs | jq 'select(.level == "ERROR")'

# Усі помилки за останню годину з конкретного логера
railway logs | jq 'select(.level == "ERROR" and .logger | startswith("apps."))'

# Тільки текст повідомлень (без JSON шуму)
railway logs | jq -r '.message'
```

`django.request` логер виставлений у `WARNING` — INFO-логи 4xx
запитів задушені, 5xx і unhandled exceptions залишаються видимими.

---

## Контакти

Якщо setup впав — звертайся до DevOps. Помилку постав у `#deploy-issues` Slack або зроби issue з тегом `infra`.
