# Error Alerts Setup — Telegram (PR-9)

> Покрокова інструкція як підключити автоматичні алерти про 5xx помилки
> у production через приватний Telegram канал. Це **cheap-tier заміна
> Sentry** — для startup-стадії, поки трафік не великий і платний APM
> не виправданий.

## Як це працює

```
500 в Django view
  ↓ Django логує в `django.request` як ERROR
  ↓ TelegramErrorHandler (apps/notifications/error_alerts.py)
    1. fingerprint = sha1(exception + path + msg[:100])
    2. Redis: `error_alert:{fp}` уже існує? Так → drop. Ні → set TTL=300s
    3. format_message → HTML-escaped, ≤4000 chars, без PII
    4. send_telegram_error_alert_task.delay(text)
       (Celery воркер виконує POST telegram.org/bot<TOKEN>/sendMessage)
```

**Що НЕ потрапляє в Telegram (GDPR-safe):**
- request body (paswords, tokens, особисті дані)
- query string (`?secret=hunter2`)
- headers (Authorization, Cookie)
- `user.email`, `user.username`, `user.full_name`

**Що потрапляє:** HTTP метод, path, `user.id` (якщо authenticated),
exception class, message head, fingerprint, traceback (head + tail).

## Setup

### Крок 1 — Створи Telegram бот через @BotFather

1. Відкрий [@BotFather](https://t.me/BotFather) у Telegram
2. Надішли команду: `/newbot`
3. BotFather запитає ім'я: `ApartmentOS Error Alerts` (або як хочеш)
4. Потім запитає username — має закінчуватись на `bot`:
   `apartmentos_errors_bot` (або інший вільний)
5. BotFather пришле повідомлення з токеном виду:
   ```
   1234567890:ABCdefGhIJKlmnoPQRStuVWXYZ-1234567890
   ```
   **Збережи токен у password manager — другого шансу не буде.**

### Крок 2 — Створи приватний канал

1. Telegram → New Channel → дай назву `ApartmentOS Errors`
2. Тип каналу → **Private** (важливо — не публічний)
3. Опис (опційно): "5xx production errors from apartmentos.org"

### Крок 3 — Додай бот як адміна каналу

1. Відкрий канал → клікни на назву зверху → **Administrators** → **Add Admin**
2. Шукай бота за username (напр. `apartmentos_errors_bot`)
3. Дай йому права:
   - ✅ **Send Messages** (обов'язково)
   - ❌ Все інше можна вимкнути
4. Save

### Крок 4 — Отримай chat_id каналу

Канал не має простого `chat_id` як у звичайних чатів. Найпростіший спосіб:

1. **Надішли будь-яке повідомлення в канал** (наприклад, "test")
   — щоб у бота з'явився update.
2. Відкрий у браузері (підстав свій токен):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Знайди в JSON відповіді блок `"channel_post"` → всередині `"chat"` →
   поле `"id"`. Це число виду `-1001234567890` (мінус і ~13 цифр).
4. **Копіюй разом зі знаком мінус** — `-1001234567890`. Збережи.

> **Якщо `getUpdates` повертає `result: []`** — або бот ще не отримав
> update (надішли ще одне повідомлення), або вже якийсь webhook
> "з'їв" event. У другому випадку — `https://api.telegram.org/bot<TOKEN>/deleteWebhook`
> і повтори.

### Крок 5 — Налаштуй env vars на Railway

Потрібно додати **на ОБИДВА сервіси** (Web + Celery Worker), бо Web
запускає handler, а Worker виконує Celery task що POSTить у Telegram.

**Web service → Settings → Variables:**
```
ERROR_ALERTS_TG_BOT_TOKEN=1234567890:ABCdefGhIJKlmnoPQRStuVWXYZ-1234567890
ERROR_ALERTS_TG_CHAT_ID=-1001234567890
```

**Celery Worker service → Settings → Variables:** ті самі дві.

> **Celery Beat не потребує** цих env vars — він тільки пушить scheduled
> tasks у чергу, не виконує `send_telegram_error_alert_task`.

Після збереження Railway автоматично redeploy сервіси.

### Крок 6 — Перевірка

#### Варіант А — trigger fake 500 через Django shell

```bash
# Web service → Logs → Run Command:
python manage.py shell
```

```python
import logging
logger = logging.getLogger("django.request")
try:
    raise RuntimeError("PR-9 smoke test — please ignore")
except Exception:
    logger.error("test 500", exc_info=True)
```

Через 1-3 секунди в Telegram канал має прийти повідомлення:
```
🚨 5xx Production Error
Exception: RuntimeError
Message: test 500
Fingerprint: <hash>
<traceback>
```

#### Варіант Б — налаштуй reproducer view

(Тільки тимчасово!) Додай у будь-який urlpatterns:
```python
path("smoke500/", lambda r: 1/0),
```
GET https://apartmentos.org/smoke500/ → ZeroDivisionError → Telegram алерт. **Не забудь видалити** після перевірки.

## Troubleshooting

### Бот не пише в канал

| Симптом | Причина | Fix |
|---|---|---|
| `/getUpdates` повертає `{}` | Webhook вже встановлений | `GET /bot<TOKEN>/deleteWebhook` |
| `Forbidden: bot is not a member of the channel chat` | Бот не доданий як адмін | Додай бот як адміна з правом Send Messages |
| `Bad Request: chat not found` | Невірний `chat_id` (без `-` або не той канал) | Перевір що `chat_id` починається з `-100` |
| Тільки в Worker logs `requests.exceptions.HTTPError: 401 Unauthorized` | Невірний токен | Скопіюй токен ще раз з @BotFather |
| Усе ОК у логах, але повідомлень немає | Канал muted у телефоні | Розмутити в Telegram |

### Алерт не приходить хоча 500 точно сталась

1. **Перевір env vars на Railway** — `ERROR_ALERTS_TG_BOT_TOKEN` і
   `ERROR_ALERTS_TG_CHAT_ID` є **і** на Web, **і** на Celery Worker
2. **Перевір що handler підключений** — `python manage.py shell` →
   ```python
   import logging
   h = logging.getLogger("django.request").handlers
   print([type(x).__name__ for x in h])
   ```
   Має бути `['StreamHandler', 'TelegramErrorHandler']`
3. **Dedup window** — якщо така ж помилка вже прилетіла за останні 5 хв,
   нова замовчується. Це by design — захист від flood'у.
4. **Celery Worker працює?** — `Web → Logs` має не показувати
   "celery worker not connected" warnings.

### Канал захлинається повідомленнями під час інциденту

Збільш `dedup_window_sec` у `apps/notifications/error_alerts.py`:
```python
class TelegramErrorHandler(logging.Handler):
    def __init__(self, level=..., dedup_window_sec: int = 900):  # 15 min
```
Або підняти у LOGGING dictConfig:
```python
"telegram_alerts": {
    "()": "apps.notifications.error_alerts.TelegramErrorHandler",
    "level": "ERROR",
    "dedup_window_sec": 900,
},
```

## Архітектурні нотатки

- **Чому окремий бот, не OrganizationBot?** OrganizationBot для
  per-tenant нотифікацій (заявки, оголошення). Error alerts — це
  ops/dev tool, не для користувачів. Окремий бот легше відключити /
  передати DevOps команді / звузити access.
- **Чому Celery, а не sync HTTP?** Telegram API може лагати (timeout
  до 5s), а handler крутиться у request thread. Sync POST → 5s доданих
  до latency 500 view → користувач думає що сервер мертвий.
- **Чому 5xx, а не 4xx теж?** 4xx — це здебільшого user errors (bad
  request, 404, 403). Алерти на них — шум. 5xx завжди = bug у нас.
- **Dedup на Redis, не in-memory** — кілька web replicas мали б
  кожен свій in-memory state і кожен б надіслав alert. Redis кеш
  shared, тому під час outage = 1 alert на cluster, не N.
