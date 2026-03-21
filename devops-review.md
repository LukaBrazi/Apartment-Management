# DevOps Review — Skandi Apartments
> Дата: 2026-03-21 | Переглянуто: Dockerfile, docker-compose.local.yml, docker-compose.ci.yml, nginx конфіги, railway.toml, settings/production.py, settings/base.py, requirements/*.txt, .github/workflows/ci.yml

---

## 🔴 Production Blockers

### 1. Відсутній `docker-compose.prod.yml` — деплой непрозорий
**Файл:** `railway.toml`, `.github/workflows/ci.yml` (рядки 151–156)

**Проблема:** CD-крок у CI закоментований і посилається на `docker-compose.prod.yml`, якого не існує. Вся production-конфігурація тримається виключно на Railway nixpacks і `railway.toml`. Якщо потрібно мігрувати на VPS, Render або self-hosted — немає нічого готового.

**Рішення:** Створити `docker-compose.prod.yml` з gunicorn, nginx (з SSL), celery worker/beat, і задокументувати варіант non-Railway деплою.

---

### 2. `makemigrations` запускається в `start` скрипті
**Файл:** `compose/local/server/start` (рядок 13)

**Проблема:** `python manage.py makemigrations --no-input` в entrypoint — критична помилка. Якщо хтось скопіює цей скрипт у production або запустить не той entrypoint, автоматично згенеруються нові міграції прямо в production-контейнері. Міграції завжди повинні бути під контролем версій, а не генеруватися на льоту.

**Рішення:** Видалити `makemigrations` зі скрипту запуску. Залишити тільки `migrate`. Міграції мають генеруватися локально і комітитися в git.

```bash
# Правильно:
python manage.py migrate --no-input
python manage.py collectstatic --no-input
exec python manage.py runserver_plus ...
```

---

### 3. Контейнер запускається від `root`
**Файл:** `compose/local/server/Dockerfile`

**Проблема:** Dockerfile не визначає non-root користувача (`USER`). Всі процеси (Django, Celery) запускаються від root. Якщо зловмисник отримає RCE через уразливість у залежностях — він матиме root-доступ до контейнера і потенційно до host через volume mounts.

**Рішення:** Додати non-root user у Dockerfile перед `ENTRYPOINT`:

```dockerfile
# Після встановлення залежностей, перед COPY app:
RUN addgroup --system django && adduser --system --ingroup django django
RUN chown -R django:django ${APP_HOME}
USER django
```

---

### 4. Telegram bot — лише polling, без production webhook
**Файл:** `docker-compose.local.yml` (рядок 208), `railway.toml`

**Проблема:** Bot запускається через `python manage.py run_bot` (polling), що є нормальним для local dev. Але в `railway.toml` немає жодного згадування про Telegram bot service — тобто бот або взагалі не запускається в production, або потребує ручного налаштування окремого Railway сервісу без документації.

**Рішення:** Для production використовувати webhook-режим. Додати в `railway.toml` коментар або окремий сервіс:
```
startCommand = "cd server && python manage.py set_webhook --domain=https://your-domain.railway.app"
```
Або задокументувати в README кроки для webhook setup.

---

## 🟠 Важливо для стабільності

### 5. Gunicorn запускається з лише 2 воркерами
**Файл:** `railway.toml` (рядок 7)

**Проблема:** `--workers 2` — мінімально допустиме значення для production під навантаженням. При обробці I/O-bound задач (DB, R2 storage) 2 воркери можуть стати вузьким місцем. Gunicorn рекомендує `2 * CPU_count + 1`.

**Рішення:**
```toml
startCommand = "cd server && python manage.py migrate --no-input && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers ${GUNICORN_WORKERS:-4} --worker-class gthread --threads 2 --timeout 120 --access-logfile -"
```
Встановити `GUNICORN_WORKERS=4` як Railway env variable.

---

### 6. Celery worker в production з `--concurrency=1`
**Файл:** `railway.toml` (рядок 12, коментар)

**Проблема:** Закоментована команда для Celery worker має `--concurrency=1`. Для I/O-bound задач (email через SMTP, HTTP-запити) це занадто мало. Всі завдання виконуються послідовно.

**Рішення:**
```bash
celery -A config.celery_app worker --loglevel=info --concurrency=4 --pool=gevent
```
Для Railway: встановити `CELERY_CONCURRENCY=4` і використовувати `gevent` pool для I/O-bound задач (потрібен `pip install gevent`).

---

### 7. Redis без автентифікації (local) та без `restart` policy
**Файл:** `docker-compose.local.yml` (рядок 96–108)

**Проблема (1):** Redis сервіс не має `restart: unless-stopped`. Якщо Redis впаде, Celery і Django cache перестануть працювати, але контейнер не перезапуститься автоматично.

**Проблема (2):** `.envs/.local/.django.env` — Redis URL без пароля (`redis://redis:6379/0`). Для local це прийнятно, але варто додати захист навіть у dev-середовищі.

**Рішення:**
```yaml
redis:
  image: redis:6-alpine  # alpine замість стандартного
  restart: unless-stopped
  command: redis-server --requirepass ${REDIS_PASSWORD:-devpassword}
```

---

### 8. Відсутній Sentry — немає error tracking в production
**Файли:** `server/requirements/production.txt`, `server/config/settings/production.py`

**Проблема:** У production settings немає жодного error tracking сервісу. Помилки 500 логуються лише в stdout, і їх ніхто не побачить, якщо не дивитися в Railway logs вручну.

**Рішення:** Додати Sentry:
```
# requirements/production.txt
sentry-sdk[django]==2.x.x
```
```python
# settings/production.py
import sentry_sdk
sentry_sdk.init(
    dsn=env("SENTRY_DSN", default=""),
    environment="production",
    traces_sample_rate=0.1,
)
```
Встановити `SENTRY_DSN` в Railway variables.

---

### 9. Немає `restart` policies у ключових сервісах
**Файл:** `docker-compose.local.yml`

**Проблема:** Жоден сервіс (server, postgres, redis, celeryworker, celerybeat, nginx) не має `restart: unless-stopped`. При падінні контейнера Docker не перезапустить його автоматично. Особливо критично для celerybeat — якщо він впав, заплановані задачі (`update-reputations-every-day`) не виконуватимуться.

**Рішення:** Додати до кожного production-сервісу:
```yaml
restart: unless-stopped
```
Для `celerybeat` варто `restart: always`.

---

## 🟡 Оптимізації

### 10. Dockerfile: `git` встановлюється окремим шаром + не потрібен в production
**Файл:** `compose/local/server/Dockerfile` (рядки 54–55)

**Проблема:** `git` встановлюється окремою командою після того як вже зроблено `rm -rf /var/lib/apt/lists/*`. Це означає повторний `apt-get update`, зайвий layer, і ~30MB до розміру образу. При тому `git` зазвичай не потрібен у production образі.

**Рішення:** Об'єднати в один RUN:
```dockerfile
RUN apt-get update && apt-get install --no-install-recommends -y \
    libpq-dev \
    gettext \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*
```
Якщо git потрібен (наприклад для pip install з git-URL), додати його разом з іншими пакетами.

---

### 11. Nginx: відсутній gzip та security headers
**Файли:** `compose/local/nginx/default.conf`, `compose/ci/nginx/default.conf`

**Проблема:** Nginx не має увімкненого gzip-стиснення для статичних ресурсів і API-відповідей. Також відсутні security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).

**Рішення:** Додати в `server {}` блок:
```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/javascript application/json application/javascript;

add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

---

### 12. Nginx: відсутнє rate limiting для API
**Файл:** `compose/local/nginx/default.conf`

**Проблема:** Немає `limit_req_zone` для `/api/v1/` та `/django-admin/`. DRF throttling (`200/day anon`, `500/day user`) є, але воно на рівні Django — запити все одно доходять до Gunicorn. Brute-force на `/api/v1/auth/` не обмежений на рівні nginx.

**Рішення:**
```nginx
# В http блоці (або окремий .conf):
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=admin:10m rate=2r/s;

# В location /api/v1/:
limit_req zone=api burst=20 nodelay;

# В location /django-admin/:
limit_req zone=admin burst=5;
```

---

### 13. CI: Docker layer cache завжди інвалідується
**Файл:** `.github/workflows/ci.yml` (рядки 59–64)

**Проблема:** Cache key — `${{ runner.os }}-buildx-${{ github.sha }}`. `github.sha` унікальний для кожного коміту, тому кеш ніколи не відновлюється з попередніх builds. Кожен CI run будує образ з нуля (~3–5 хвилин зайвих витрат).

**Рішення:**
```yaml
key: ${{ runner.os }}-buildx-${{ hashFiles('compose/**', 'server/requirements/**') }}
restore-keys: |
  ${{ runner.os }}-buildx-
```

---

### 14. `CELERY_TASK_SOFT_TIME_LIMIT = 60` — занадто мало для email задач
**Файл:** `server/config/settings/base.py` (рядок 242)

**Проблема:** `CELERY_TASK_SOFT_TIME_LIMIT = 60` (секунд) може вбити email-задачу через `djcelery_email`, якщо SMTP сервер відповідає повільно (наприклад Resend під навантаженням). `CELERY_TASK_TIME_LIMIT = 5 * 60` (hard limit) — краще, але soft kill занадто ранній.

**Рішення:**
```python
CELERY_TASK_SOFT_TIME_LIMIT = 5 * 60   # 5 хвилин — soft
CELERY_TASK_TIME_LIMIT = 10 * 60       # 10 хвилин — hard kill
```

---

### 15. `.dockerignore` не виключає `client/node_modules`
**Файл:** `.dockerignore`

**Проблема:** `.dockerignore` виключає `.envs/` і `.git/`, але не виключає `client/node_modules/` (папка з >50K файлів) та `.idea/`. Весь build context передається в Docker daemon, що збільшує час build.

**Рішення:**
```
# .dockerignore (доповнити)
client/node_modules/
client/.next/
.idea/
**/__pycache__/
**/*.pyc
**/*.pyo
*.md
docs/
```

---

## 💡 Nice-to-have

### 16. Flower недоступний у production
**Файл:** `railway.toml`, `docker-compose.local.yml` (рядок 154–162)

**Проблема:** Flower є в local-оточенні з basic auth, але в production (Railway) не задеплоєний. Без Flower не видно стан черг Celery, failed tasks, retry-логіки.

**Рішення:** Додати окремий Railway сервіс:
```bash
cd server && celery -A config.celery_app flower \
  --basic_auth="${CELERY_FLOWER_USER}:${CELERY_FLOWER_PASSWORD}" \
  --port=5555
```

---

### 17. Автоматизований backup БД не запланований
**Файли:** `compose/local/postgres/maintenance/backup`, `server/config/settings/base.py` (CELERY_BEAT_SCHEDULE)

**Проблема:** Backup-скрипти (backup, restore, rmbackup) існують і добре написані. Але вони не запускаються автоматично — потрібен ручний запуск `docker exec postgres backup`. У production (Railway) — PostgreSQL managed, але немає scheduled backup задачі через Celery beat.

**Рішення:** Додати Celery beat task:
```python
CELERY_BEAT_SCHEDULE = {
    "daily-db-backup": {
        "task": "apps.common.tasks.backup_database",
        "schedule": crontab(hour=3, minute=0),  # щодня в 3:00 Kyiv
    },
    ...
}
```
Або увімкнути Railway автоматичні backup (є в Pro plan).

---

### 18. Swagger/ReDoc доступний у production без обмежень
**Файл:** `server/config/settings/base.py` (рядок 303), `compose/local/nginx/default.conf`

**Проблема:** `SERVE_INCLUDE_SCHEMA: False` заховує лише raw schema endpoint, але `/swagger/schema/` і `/swagger/redoc/` проксюються nginx у production. API документація публічно доступна — розкриває структуру endpoints, параметри, схеми відповідей.

**Рішення:** В production settings обмежити доступ:
```python
# settings/production.py
SPECTACULAR_SETTINGS = {
    ...
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
}
```
Або закрити nginx location block для swagger в production nginx конфігурації.

---

### 19. Hardcoded SECRET_KEY default у `settings/local.py`
**Файл:** `server/config/settings/local.py` (рядок 10)

**Проблема:** `SECRET_KEY` має hardcoded default значення прямо в коді (`QTMT8ZsZaDOSmVFhCTmJ...`). Якщо розробник запускає Django без env файлу (наприклад, у CI або тестах), цей ключ буде використаний. Якщо цей файл потрапить у публічний репозиторій — ключ скомпрометований.

**Рішення:** Прибрати default value, зробити змінну обов'язковою:
```python
SECRET_KEY = env("DJANGO_SECRET_KEY")  # без default — упаде явно якщо не задано
```

---

### 20. Немає production health probe в Railway
**Файл:** `railway.toml`

**Проблема:** Railway має лише `restartPolicyType = "on-failure"` і `restartPolicyMaxRetries = 3`. Якщо сервер запустився, але повертає 500 на всі запити — Railway не знає про це і не перезапускає сервіс.

**Рішення:** Додати health check endpoint і налаштувати Railway healthcheck (доступно в `railway.toml`):
```toml
[deploy]
healthcheckPath = "/api/v1/site-settings/"
healthcheckTimeout = 30
```
Це змусить Railway перевіряти стан сервісу і перезапускати при збоях.
