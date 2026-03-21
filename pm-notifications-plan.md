# 📋 Технічний план: Мікросервіс Telegram-нотифікацій
**Проєкт:** Skandi Apartments
**Дата:** 2026-03-21
**PM:** Project Manager Agent
**Виконавець:** Backend Developer
**Статус:** Ready for development

---

## 1. Архітектурне рішення

### Варіант A: Django App всередині основного проєкту ✅ РЕКОМЕНДОВАНО

```
server/apps/notifications/   ← новий Django app
```

**Плюси:**
- Прямий доступ до всіх моделей (Issue, VehiclePass, Announcement, etc.) без API-виклику
- Спільна БД — не потрібно синхронізувати стан
- Один Celery worker — задачі нотифікацій в тій самій черзі
- Простіше деплоїти — без додаткових контейнерів/сервісів
- Django signals — найелегантніший спосіб тригерити нотифікації
- Менше інфраструктурного overhead

**Мінуси:**
- Менша ізоляція (але для проєкту цього масштабу — не критично)

### Варіант B: Окремий мікросервіс (FastAPI + aiogram)

```
telegram-bot/    ← окремий сервіс
```

**Плюси:**
- Повна ізоляція, можна деплоїти незалежно
- Можна масштабувати окремо

**Мінуси:**
- Потрібна міжсервісна комунікація (webhook або message broker)
- Дублювання бізнес-логіки / синхронізація моделей
- Складніше в розробці та дебагінгу
- Додатковий Docker сервіс, своя БД або спільна — обидва варіанти з проблемами

### 🟢 Рекомендація: Варіант A

Для поточного масштабу проєкту (один моноліт на Django) `apps.notifications` — оптимальне рішення. Ізоляція через чіткі межі модуля. У разі потреби ізоляція в мікросервіс — окрема задача в майбутньому.

---

## 2. Події для нотифікацій

### Issue (Заявки на обслуговування)

| Подія | Тригер | Отримувач | Повідомлення |
|-------|--------|-----------|-------------|
| Нова заявка створена | `Issue` saved, status=`reported` | Dispatcher (всі диспетчери будинку) | 🔔 *Нова заявка #ID: «Назва»*\nМешканець: Ім'я, кв. №XX\nПріоритет: HIGH |
| Заявка прийнята | status: `reported` → `accepted` | Tenant (хто подав) | ✅ *Заявку #ID прийнято*\nДиспетчер взяв у роботу. SLA до: DD.MM HH:MM |
| Заявка в роботі | status: `accepted` → `in_progress` | Tenant | 🔧 *Заявку #ID взято в роботу*\nВиконавець: Ім'я |
| Заявка виконана | status: → `done` | Tenant | 🎉 *Заявку #ID виконано!*\nПросимо оцінити роботу |
| Заявка відхилена | status: → `rejected` | Tenant | ❌ *Заявку #ID відхилено*\nЗверніться до диспетчера |
| Заявка прострочена (SLA) | Celery beat, `due_at` < now | Dispatcher + Admin | ⚠️ *SLA порушено! Заявка #ID*\nПрострочена на N годин |
| Виконавець призначений | `assigned_to` змінився | Виконавець (Worker) | 📌 *Вам призначено заявку #ID: «Назва»*\nАдреса: Будинок, кв. №XX |

### VehiclePass (Перепустки на авто)

| Подія | Тригер | Отримувач | Повідомлення |
|-------|--------|-----------|-------------|
| Нова перепустка створена | `VehiclePass` saved, status=`pending` | Guard (охоронці будинку) | 🚗 *Нова перепустка*\nА/м: ABC-1234\nМешканець: кв. №XX\nДата: DD.MM.YYYY |
| Перепустка закрита | status: `pending` → `closed` | Tenant | ✅ *Перепустку закрито*\nА/м ABC-1234 від DD.MM |

### Announcement (Оголошення)

| Подія | Тригер | Отримувач | Повідомлення |
|-------|--------|-----------|-------------|
| Нове оголошення | `Announcement` created | Всі Tenant будинку | 📢 *Нове оголошення: «Назва»*\nDDD... (перші 200 символів) |

### Report / ViolationReport

| Подія | Тригер | Отримувач | Повідомлення |
|-------|--------|-----------|-------------|
| Скарга на мешканця | `Report` created | Admin | 🚨 *Нова скарга*\nВід: Ім'я на: Ім'я\nТема: «Назва» |

### Система / SLA моніторинг

| Подія | Тригер | Отримувач | Повідомлення |
|-------|--------|-----------|-------------|
| Нагадування про SLA | Celery beat щогодини | Dispatcher | ⏰ *Нагадування: N заявок близькі до SLA* |

---

## 3. Технічний стек

### Telegram Bot бібліотека

**Рекомендація: `python-telegram-bot >= 20.x` (async)**

```
python-telegram-bot==20.7
```

**Переваги над aiogram:**
- Краща документація
- Офіційна підтримка
- Легше інтегрується з синхронним Django
- PTB 20.x підтримує asyncio при потребі

**Режим роботи:** Polling (для dev) + Webhook (для production через Nginx).

### Зберігання telegram_chat_id

**Рекомендація: Окрема таблиця `TelegramProfile` (OneToOne до User)**

```python
# apps/notifications/models.py
class TelegramProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="telegram")
    chat_id = models.BigIntegerField(unique=True)
    is_active = models.BooleanField(default=True)
    # Налаштування нотифікацій
    notify_issues = models.BooleanField(default=True)
    notify_passes = models.BooleanField(default=True)
    notify_announcements = models.BooleanField(default=True)
```

**Чому не в Profile:** Profile вже перевантажений. Окрема таблиця — чіткіша відповідальність, легше відключити/видалити.

### Токен верифікації

```python
class TelegramVerificationToken(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()  # +15 хвилин від створення
```

### Інтеграція з Celery

Нотифікації — **асинхронні Celery задачі**. Ніколи не блокуємо основний потік.

```python
# Тригер через Django signal:
@receiver(post_save, sender=Issue)
def issue_status_changed(sender, instance, created, **kwargs):
    if created:
        notify_dispatchers_new_issue.delay(instance.pk)
    # ...

# Celery task:
@shared_task(name="notify_dispatchers_new_issue", max_retries=3, default_retry_delay=60)
def notify_dispatchers_new_issue(issue_id: int) -> None:
    ...
```

**Retry policy:** 3 спроби з інтервалом 60 секунд — на випадок Telegram API тимчасово недоступний.

---

## 4. User Story: Підключення Telegram акаунту

### Flow

```
[Веб-додаток] → Генерує токен → Відображає посилання/кнопку
     ↓
[Мешканець] → Клікає "Підключити Telegram"
     ↓
[Відкривається Telegram] → Бот → /start <token>
     ↓
[Бот] → Валідує токен → Зберігає chat_id → Підтверджує
     ↓
[API] → Помічає токен як використаний → Активує TelegramProfile
```

### Детальний опис

1. **Мешканець** в особистому кабінеті натискає "Підключити Telegram".
2. **Frontend** робить `POST /api/v1/notifications/telegram/generate-token/` → отримує `token` (UUID).
3. **Frontend** показує кнопку-посилання: `https://t.me/SkandiBotName?start=<token>` або QR-код.
4. **Мешканець** натискає → відкривається Telegram → натискає "Start".
5. **Telegram Bot** отримує команду `/start <token>`.
6. **Bot handler** → `POST /api/v1/notifications/telegram/verify/` з `{token, chat_id}`.
7. **API** перевіряє токен (не прострочений, не використаний), створює `TelegramProfile`, повертає дані користувача.
8. **Бот** відповідає: *"✅ Ваш акаунт успішно підключено! Тепер ви отримуватимете сповіщення від Skandi Apartments."*
9. **Frontend** отримує `webhook` або `polling` → оновлює стан сторінки.

### Повторне підключення / відключення

- `DELETE /api/v1/notifications/telegram/disconnect/` — видаляє `TelegramProfile`.
- Бот отримує команду `/stop` → деактивує `is_active = False`.

---

## 5. Список задач для Backend Developer

| # | Задача | Опис | SP | Пріоритет |
|---|--------|------|----|-----------|
| **SETUP** |||||
| 1 | Створити Django app `notifications` | `python manage.py startapp notifications`, додати в `INSTALLED_APPS`, базову структуру файлів | 1 | 🔴 High |
| 2 | Встановити та налаштувати `python-telegram-bot` | `pip install python-telegram-bot==20.7`, налаштувати `TELEGRAM_BOT_TOKEN` в settings/env | 1 | 🔴 High |
| **MODELS & MIGRATIONS** |||||
| 3 | Створити модель `TelegramProfile` | OneToOne до User, поля: `chat_id`, `is_active`, `notify_issues`, `notify_passes`, `notify_announcements` | 2 | 🔴 High |
| 4 | Створити модель `TelegramVerificationToken` | UUID токен, `user FK`, `is_used`, `expires_at` (+15 хв), автоматичне очищення прострочених | 2 | 🔴 High |
| 5 | Зробити та застосувати міграції | `makemigrations notifications && migrate` | 1 | 🔴 High |
| **TELEGRAM BOT** |||||
| 6 | Реалізувати Telegram Bot (`bot.py`) | Handlers: `/start <token>`, `/stop`, `/help`, `/status`. Management command `python manage.py run_bot` для polling режиму | 3 | 🔴 High |
| 7 | Реалізувати webhook endpoint | `POST /api/v1/notifications/telegram/webhook/` — приймає updates від Telegram у production. `AllowAny` permission, перевірка секретного токена | 2 | 🟡 Medium |
| **API ENDPOINTS** |||||
| 8 | `POST /generate-token/` | Генерує `TelegramVerificationToken` для поточного юзера. Повертає `{token, bot_url, expires_at}`. Rate limit: 1 токен/хв | 2 | 🔴 High |
| 9 | `POST /verify/` (internal/bot) | Internal endpoint для бота: отримує `{token, chat_id}`, валідує, створює `TelegramProfile`. Авторизація через `TELEGRAM_INTERNAL_SECRET` | 2 | 🔴 High |
| 10 | `GET /status/` | Повертає стан підключення для поточного юзера: `{connected: bool, chat_id_masked: str, settings: {...}}` | 1 | 🔴 High |
| 11 | `DELETE /disconnect/` | Видаляє `TelegramProfile` поточного юзера, надсилає повідомлення в Telegram | 1 | 🟡 Medium |
| 12 | `PATCH /settings/` | Оновлює налаштування нотифікацій: `{notify_issues, notify_passes, notify_announcements}` | 1 | 🟡 Medium |
| **CELERY TASKS** |||||
| 13 | Базова утиліта відправки повідомлень | `send_telegram_message(chat_id, text, parse_mode="HTML")` з retry логікою. Обробка `ChatNotFound`, `BotBlocked` — автоматично деактивує `TelegramProfile` | 2 | 🔴 High |
| 14 | Tasks для Issue-нотифікацій | `notify_dispatchers_new_issue`, `notify_tenant_issue_status_changed`, `notify_worker_assigned`, `notify_sla_overdue` | 3 | 🔴 High |
| 15 | Tasks для VehiclePass-нотифікацій | `notify_guards_new_pass`, `notify_tenant_pass_closed` | 2 | 🟡 Medium |
| 16 | Tasks для Announcement-нотифікацій | `notify_building_tenants_announcement` — масова розсилка через будинок | 2 | 🟡 Medium |
| **SIGNALS** |||||
| 17 | Django Signals для тригерів | `signals.py` в `notifications` app: підписатись на `post_save` для Issue, VehiclePass, Announcement, Report. Підключити в `apps.py` через `ready()` | 3 | 🔴 High |
| **SLA MONITORING** |||||
| 18 | Celery Beat задача SLA-моніторингу | `check_sla_violations` — запускається щогодини, знаходить `Issue` де `due_at < now + 2h` і `status not in [done, rejected]`, надсилає попередження диспетчерам | 2 | 🟡 Medium |
| **ADMIN** |||||
| 19 | Django Admin для `notifications` | Реєстрація `TelegramProfile`, `TelegramVerificationToken` в адмінці. Фільтри, пошук, можливість вручну відправити тест-повідомлення | 1 | 🟢 Low |
| **TESTING** |||||
| 20 | Unit tests | Тести для tasks (mock Telegram API), serializers, token генерації/валідації. Coverage ≥ 80% для нового модуля | 3 | 🟡 Medium |

**Загальна оцінка: ~38 Story Points (~2.5–3 тижні для 1 dev)**

---

## 6. API Endpoints

Базовий префікс: `/api/v1/notifications/telegram/`

### Підключення Telegram

```
POST   /api/v1/notifications/telegram/generate-token/
```
**Auth:** IsAuthenticated
**Request:** `{}` (порожнє тіло)
**Response:**
```json
{
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "bot_url": "https://t.me/SkandiBotName?start=550e8400-e29b-41d4-a716-446655440000",
  "expires_at": "2026-03-21T12:15:00+02:00"
}
```

---

```
POST   /api/v1/notifications/telegram/verify/
```
**Auth:** `X-Telegram-Secret: <TELEGRAM_INTERNAL_SECRET>` (тільки для внутрішнього бота)
**Request:**
```json
{
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "chat_id": 123456789
}
```
**Response:**
```json
{
  "success": true,
  "user_name": "Іван Петренко",
  "message": "Акаунт успішно підключено"
}
```

---

```
GET    /api/v1/notifications/telegram/status/
```
**Auth:** IsAuthenticated
**Response:**
```json
{
  "connected": true,
  "chat_id_masked": "***456789",
  "connected_at": "2026-03-20T10:30:00+02:00",
  "settings": {
    "notify_issues": true,
    "notify_passes": true,
    "notify_announcements": true
  }
}
```

---

```
DELETE /api/v1/notifications/telegram/disconnect/
```
**Auth:** IsAuthenticated
**Response:** `204 No Content`

---

```
PATCH  /api/v1/notifications/telegram/settings/
```
**Auth:** IsAuthenticated
**Request:**
```json
{
  "notify_issues": true,
  "notify_passes": false,
  "notify_announcements": true
}
```
**Response:** `200 OK` з оновленими settings

---

```
POST   /api/v1/notifications/telegram/webhook/
```
**Auth:** `X-Telegram-Bot-Api-Secret-Token: <header>` (Telegram webhook secret)
**Використання:** тільки в production, Telegram надсилає updates на цей URL
**Response:** `200 OK` (завжди, щоб Telegram не retry-їв)

---

```
POST   /api/v1/notifications/telegram/test/   (тільки для DEBUG=True)
```
**Auth:** IsAuthenticated (Admin only)
**Request:** `{}` — надсилає тестове повідомлення на підключений акаунт
**Response:** `{"sent": true}`

---

## 7. Структура файлів нового модуля

```
server/apps/notifications/
├── __init__.py
├── apps.py                    # NotificationsConfig з ready() для signals
├── admin.py                   # Реєстрація моделей в Django Admin
├── models.py                  # TelegramProfile, TelegramVerificationToken
├── serializers.py             # GenerateTokenSerializer, VerifyTokenSerializer, SettingsSerializer
├── views.py                   # GenerateTokenView, VerifyView, StatusView, DisconnectView, SettingsView, WebhookView
├── urls.py                    # urlpatterns
├── signals.py                 # post_save receivers для Issue, VehiclePass, Announcement, Report
├── tasks.py                   # Всі Celery tasks для нотифікацій
├── bot.py                     # Telegram Bot: handlers, ApplicationBuilder
├── utils.py                   # send_telegram_message(), get_dispatchers_for_building(), etc.
├── permissions.py             # TelegramBotPermission (перевірка internal secret)
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py
└── management/
    └── commands/
        ├── __init__.py
        └── run_bot.py         # Management command для запуску polling

server/apps/notifications/tests/
├── __init__.py
├── test_models.py
├── test_views.py
├── test_tasks.py
└── test_signals.py
```

### Ключові фрагменти коду

**`apps.py`:**
```python
class NotificationsConfig(AppConfig):
    name = "apps.notifications"
    verbose_name = "Notifications"

    def ready(self):
        import apps.notifications.signals  # noqa: F401
```

**`signals.py` (структура):**
```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.issues.models import Issue
from apps.passes.models import VehiclePass
from apps.posts.models import Announcement
from .tasks import (
    notify_dispatchers_new_issue,
    notify_tenant_issue_status_changed,
    notify_guards_new_pass,
    notify_building_tenants_announcement,
)

@receiver(post_save, sender=Issue)
def on_issue_saved(sender, instance, created, update_fields, **kwargs):
    if created:
        notify_dispatchers_new_issue.delay(instance.pk)
    else:
        # Перевірити зміну статусу
        notify_tenant_issue_status_changed.delay(instance.pk)
```

**`utils.py`:**
```python
import logging
from telegram import Bot
from django.conf import settings
from .models import TelegramProfile

logger = logging.getLogger(__name__)

def send_telegram_message(chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Синхронна відправка повідомлення. Викликати тільки з Celery task."""
    import asyncio
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        asyncio.run(bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode))
        return True
    except Exception as e:
        logger.error(f"Telegram send error to {chat_id}: {e}")
        # Деактивувати якщо бот заблокований
        if "bot was blocked" in str(e).lower() or "chat not found" in str(e).lower():
            TelegramProfile.objects.filter(chat_id=chat_id).update(is_active=False)
        return False

def get_dispatchers_for_issue(issue) -> list[int]:
    """Повертає список chat_id диспетчерів для конкретного будинку."""
    from apps.profiles.models import Profile
    profiles = Profile.objects.filter(
        occupation__in=[Profile.Occupation.DISPATCHER, Profile.Occupation.ADMIN],
        user__telegram__is_active=True,
    ).select_related("user__telegram")
    # Фільтрація по будинку якщо є buildings у профілі
    return [p.user.telegram.chat_id for p in profiles if hasattr(p.user, 'telegram')]
```

---

## 8. Конфігурація

### Змінні середовища

Додати до `.envs/.local/.django.env` та `.envs/.production/.django.env`:

```bash
# ── Telegram Bot ─────────────────────────────────────────────────────────────

# Токен бота від @BotFather
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Ім'я бота (без @), для генерації посилань
TELEGRAM_BOT_USERNAME=SkandiBotName

# Секрет для внутрішнього verify endpoint (bot → django)
TELEGRAM_INTERNAL_SECRET=your_random_secret_here_min_32_chars

# Production webhook URL (тільки для prod)
# TELEGRAM_WEBHOOK_URL=https://yourdomain.com/api/v1/notifications/telegram/webhook/

# Секрет для верифікації webhook від Telegram
# TELEGRAM_WEBHOOK_SECRET=another_random_secret_here
```

### Django Settings (`base.py`)

Додати в `server/config/settings/base.py`:

```python
# ── Telegram Notifications ───────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="")
TELEGRAM_INTERNAL_SECRET = env("TELEGRAM_INTERNAL_SECRET", default="")
TELEGRAM_WEBHOOK_URL = env("TELEGRAM_WEBHOOK_URL", default="")
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", default="")
TELEGRAM_VERIFICATION_TOKEN_TTL_MINUTES = 15
```

Додати в `INSTALLED_APPS` → `LOCAL_APPS`:
```python
LOCAL_APPS = [
    ...
    "apps.notifications",  # ← додати
]
```

### `requirements/base.txt`

```
python-telegram-bot==20.7
```

### `config/urls.py`

```python
path("api/v1/notifications/", include("apps.notifications.urls")),
```

### Celery Beat (`base.py`)

Додати в `CELERY_BEAT_SCHEDULE`:

```python
CELERY_BEAT_SCHEDULE = {
    "update-reputations-every-day": {
        "task": "update_all_reputations",
        "schedule": timedelta(days=1),
    },
    # ← додати:
    "check-sla-violations-hourly": {
        "task": "notifications.check_sla_violations",
        "schedule": timedelta(hours=1),
    },
}
```

### Docker changes

#### `docker-compose.local.yml` — Додати сервіс Telegram Bot Polling

```yaml
  # Telegram Bot (polling mode for local dev)
  telegrambot:
    <<: *server
    container_name: alpha_apartments_local_telegrambot
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      server:
        condition: service_healthy
    ports: []
    command: python manage.py run_bot
    networks:
      - alpha_apartments_network
    profiles:
      - telegram  # Запускати тільки якщо потрібно: docker compose --profile telegram up
```

> **Примітка:** Використання `profiles: [telegram]` дозволяє запускати бота опціонально командою:
> ```bash
> docker compose --profile telegram up
> ```
> Без `--profile telegram` — бот не запускається (зручно коли токен ще не налаштований).

#### Production (webhook mode)

У production **не потрібен окремий контейнер**. Telegram сам надсилає оновлення на webhook URL. Потрібно лише зареєструвати webhook один раз:

```bash
# Команда для реєстрації webhook (запустити один раз після деплою)
python manage.py shell -c "
import asyncio
from telegram import Bot
from django.conf import settings
bot = Bot(settings.TELEGRAM_BOT_TOKEN)
asyncio.run(bot.set_webhook(
    url=settings.TELEGRAM_WEBHOOK_URL,
    secret_token=settings.TELEGRAM_WEBHOOK_SECRET
))
print('Webhook set!')
"
```

Або додати Management command `python manage.py setup_telegram_webhook`.

---

## 9. Порядок виконання (рекомендований)

```
Sprint 1 (High Priority):
  Задачі: 1, 2, 3, 4, 5, 6, 8, 9, 10, 13, 14, 17

Sprint 2 (Medium Priority):
  Задачі: 7, 11, 12, 15, 16, 18, 20

Sprint 3 (Polish):
  Задачі: 19 + ручне тестування з реальним ботом
```

---

## 10. Важливі технічні нюанси

### Проблема: відстеження зміни статусу Issue

Поточна модель `Issue.save()` не передає `update_fields`. Потрібно зберігати попередній статус для коректного тригера нотифікацій. **Рекомендований підхід:**

```python
# В signals.py — отримувати old_status через pre_save:
from django.db.models.signals import pre_save

_issue_old_status = {}

@receiver(pre_save, sender=Issue)
def cache_issue_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            _issue_old_status[instance.pk] = Issue.objects.get(pk=instance.pk).status
        except Issue.DoesNotExist:
            pass

@receiver(post_save, sender=Issue)
def on_issue_saved(sender, instance, created, **kwargs):
    if created:
        notify_dispatchers_new_issue.delay(instance.pk)
        return

    old_status = _issue_old_status.pop(instance.pk, None)
    if old_status and old_status != instance.status:
        notify_tenant_issue_status_changed.delay(instance.pk, old_status, instance.status)
```

### Масова розсилка (Announcement)

Для великих будинків розсилка може займати час. **Використовувати Celery chord або group:**

```python
from celery import group

@shared_task(name="notifications.notify_building_tenants_announcement")
def notify_building_tenants_announcement(announcement_id: int):
    announcement = Announcement.objects.get(pk=announcement_id)
    chat_ids = TelegramProfile.objects.filter(
        user__profile__unit__building=announcement.building,
        is_active=True,
        notify_announcements=True,
    ).values_list("chat_id", flat=True)

    tasks = group(
        send_single_announcement_notification.s(chat_id, announcement_id)
        for chat_id in chat_ids
    )
    tasks.delay()
```

### Thread Safety

`python-telegram-bot` 20.x використовує asyncio. При виклику з синхронного Celery worker використовувати `asyncio.run()` або `nest_asyncio`. Рекомендується ізолювати весь async код в `utils.py`.

---

*Документ підготовлений PM Agent на основі аналізу кодової бази проєкту Skandi Apartments станом на 2026-03-21.*
