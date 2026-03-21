# Security Audit — Skandi Apartments

**Дата:** 2026-03-21
**Аудитор:** Claude Security Engineer
**Стек:** Django 4.2 + DRF + Next.js 14
**Охоплення:** `server/` (backend), `client/` (frontend), `.envs/`, конфігурація

---

## 🔴 Критично (негайно виправити)

---

### [CRIT-1] `.envs/.local/` файли з секретами потрапили до git-репозиторію

**Файли:**
- `.envs/.local/.django.env`
- `.envs/.local/.postgres.env`
- `.envs/.local/.minio.env`

**Опис:**
Директорія `.envs/.local/` **відстежується git** (підтверджено `git ls-files .envs`). Файли містять відкритий текст з credentials:

```
POSTGRES_PASSWORD=alpha_password
DATABASE_URL=postgres://alpha_user:alpha_password@postgres:5432/alpha_apartments
MINIO_STORAGE_ACCESS_KEY=minioadmin
MINIO_STORAGE_SECRET_KEY=minioadmin123
DJANGO_SECRET_KEY=local-dev-secret-key-change-in-production-abc123xyz
```

**PoC:**
```bash
git log --all --full-history -- .envs/.local/.django.env
# Credentials будуть присутні у повній git-історії навіть якщо файли видалені
```

**Рекомендація:**
1. Негайно видалити файли з git-tracking: `git rm -r --cached .envs/.local/`
2. Додати до `.gitignore`: `.envs/.local/`
3. Ротувати ВСІ скомпрометовані паролі та ключі
4. Перевірити git-histорію на наявність production секретів: `git log -p -- .envs/`

---

### [CRIT-2] Mass Assignment — привілейована ескалація через `occupation`

**Файл:** `server/apps/profiles/serializers.py`, рядки 186–196
**Файл:** `server/apps/profiles/views.py`, рядки 163–234

**Опис:**
`UpdateProfileSerializer` включає поле `occupation` як **writeable**. `ProfileUpdateAPIView` використовує лише глобальний `IsAuthenticated` (без `permission_classes` override) і повертає профіль поточного користувача. Будь-який аутентифікований мешканець може змінити своє `occupation` на `guard` або будь-яке інше значення.

```python
# serializers.py — рядок 186–196
fields = [
    ...
    "occupation",   # ← WRITABLE! Немає жодного обмеження
    "phone_number",
]
```

**PoC:**
```bash
# Тенант (occupation=tenant) підвищує себе до guard
curl -X PATCH https://api.example.com/api/v1/profiles/me/update/ \
  -H "Cookie: access=<tenant_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"occupation": "guard"}'
# → Тенант тепер може закривати VehiclePass та переглядати всі перепустки
```

**Рекомендація:**
Видалити `occupation` з `UpdateProfileSerializer.Meta.fields`. Для зміни ролі — окремий admin-only endpoint або через `ProfileAdminUpdateAPIView`.

---

### [CRIT-3] Відсутня валідація типу та розміру файлу при завантаженні аватара

**Файл:** `server/apps/profiles/serializers.py`, рядки 234–258
**Файл:** `server/apps/profiles/views.py`, рядки 237–333

**Опис:**
`AvatarUploadSerializer` не визначає жодних обмежень на тип файлу або розмір. Зловмисник може завантажити:
- SVG із вбудованим JavaScript (XSS через зображення)
- Надвеликі файли (DoS/storage exhaustion)
- PHP/Python файли (якщо storage помилково виконує скрипти)

```python
class AvatarUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["avatar"]
        # ← НЕМАЄ validate_avatar, НЕМАЄ MAX_SIZE, НЕМАЄ content_type check
```

```python
# views.py — розширення береться з імені файлу без перевірки
ext = os.path.splitext(image.name)[1]  # довіряємо клієнту
```

**PoC:**
```bash
curl -X PATCH https://api.example.com/api/v1/profiles/avatar/upload/ \
  -H "Cookie: access=<jwt>" \
  -F "avatar=@malicious.svg;type=image/jpeg"
# → SVG з <script> завантажується у storage і може виконатися у браузері
```

**Рекомендація:**
```python
def validate_avatar(self, image):
    ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
    MAX_SIZE_MB = 5
    if image.content_type not in ALLOWED_TYPES:
        raise serializers.ValidationError("Дозволені лише JPEG, PNG, WebP.")
    if image.size > MAX_SIZE_MB * 1024 * 1024:
        raise serializers.ValidationError(f"Файл не може перевищувати {MAX_SIZE_MB}MB.")
    return image
```

---

### [CRIT-4] Logout не інвалідує refresh-токен на сервері

**Файл:** `server/apps/users/views.py`, рядки 269–306

**Опис:**
`LogoutAPIView` лише видаляє cookies на клієнті, але **не вносить refresh-токен у blacklist** на сервері. Refresh-токен залишається дійсним ще 24 години після logout. Зловмисник, який перехопив refresh-токен, може продовжувати отримувати нові access-токени.

```python
def post(self, request, ...):
    res = Response(status=status.HTTP_204_NO_CONTENT)
    res.delete_cookie("access")
    res.delete_cookie("refresh")
    res.delete_cookie("logged_in")
    return res
    # ← Токен НЕ ДОДАЄТЬСЯ до blacklist
```

**PoC:**
```bash
# 1. Перехопити refresh cookie до logout
# 2. Відправити запит на logout
# 3. Використати збережений refresh-токен для отримання нового access
curl -X POST https://api.example.com/api/v1/auth/jwt/refresh/ \
  -d '{"refresh": "<intercepted_refresh_token>"}'
# → Успіх, новий access-токен отримано попри logout
```

**Рекомендація:**
Підключити `rest_framework_simplejwt.token_blacklist`:
```python
# settings/base.py
INSTALLED_APPS += ["rest_framework_simplejwt.token_blacklist"]
SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] = True

# views.py — LogoutAPIView
from rest_framework_simplejwt.tokens import RefreshToken
refresh_token = request.COOKIES.get("refresh")
if refresh_token:
    token = RefreshToken(refresh_token)
    token.blacklist()
```

---

## 🟠 Високий ризик

---

### [HIGH-1] Default JWT signing key у коді

**Файл:** `server/config/settings/base.py`, рядок 313

**Опис:**
Якщо змінна `DJANGO_SECRET_KEY` не встановлена в оточенні, JWT підписується ключем `"test-signing-key-change-in-production"` — очевидним значенням, яке легко вгадати.

```python
SIMPLE_JWT = {
    "SIGNING_KEY": env.str("DJANGO_SECRET_KEY", default="test-signing-key-change-in-production"),
    ...
}
```

**PoC:**
Знаючи дефолтний ключ, атакуючий може підробляти JWT-токени для будь-якого `user_id`.

**Рекомендація:**
```python
"SIGNING_KEY": env.str("DJANGO_SECRET_KEY"),  # Без default — помилка якщо не встановлено
```

---

### [HIGH-2] Відсутній специфічний rate-limit на auth-endpoints

**Файл:** `server/config/settings/base.py`, рядки 285–293

**Опис:**
Глобальний throttling — `200/day` (anon) та `500/day` (user). Це лише добовий ліміт без обмежень per-minute. Для login/register/password-reset відсутній окремий жорсткий throttle, що дозволяє burst-атаки (brute force паролів за кілька секунд).

```python
"DEFAULT_THROTTLE_RATES": {
    "anon": "200/day",   # 200 запитів на день = ~8 запитів/год, але можна всі 200 за 1 хвилину!
    "user": "500/day",
}
# Немає: "login": "5/minute", "register": "10/hour"
```

**PoC:**
```bash
for i in {1..200}; do
  curl -X POST https://api.example.com/api/v1/auth/jwt/create/ \
    -d '{"email":"victim@example.com","password":"attempt'$i'"}' &
done
# → Burst brute-force 200 спроб до першого 429
```

**Рекомендація:**
```python
"DEFAULT_THROTTLE_RATES": {
    "anon": "200/day",
    "user": "500/day",
    "login": "5/minute",
    "register": "10/hour",
    "password_reset": "3/hour",
}
# + ScopedRateThrottle на відповідних views
```

---

### [HIGH-3] Відсутня CORS конфігурація для local-оточення

**Файл:** `server/config/settings/local.py`

**Опис:**
У `local.py` відсутній параметр `CORS_ALLOWED_ORIGINS`. У production він визначається через env-var (`env.list("CORS_ALLOWED_ORIGINS")`), але в `base.py` встановлено лише `CORS_URLS_REGEX`. Якщо `CORS_ALLOWED_ORIGINS` не визначений і `CORS_ALLOW_ALL_ORIGINS` не встановлений, поведінка залежить від версії django-cors-headers і може відхиляти або приймати всі запити непередбачуваним чином.

**Рекомендація:**
Явно додати до `local.py`:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

---

### [HIGH-4] Hardcoded credentials у `seed_demo.py` + небезпечний вивід у stdout

**Файл:** `server/apps/common/management/commands/seed_demo.py`

**Опис:**
Команда `seed_demo` створює demo-користувачів з фіксованим паролем `Demo1234!` та виводить credentials у stdout:

```python
dispatcher.set_password("Demo1234!")
self.stdout.write(f"  ✓ Dispatcher: {dispatcher.email} / Demo1234!")
```

Якщо команду випадково запустять у production, credentials будуть у логах та в системі.

**Рекомендація:**
1. Заборонити запуск у production через перевірку `settings.DEBUG`
2. Не виводити паролі в stdout
3. Генерувати паролі рандомно: `User.objects.make_random_password()`

---

### [HIGH-5] API документація (Swagger/ReDoc) доступна будь-якому аутентифікованому користувачу

**Файл:** `server/config/urls.py`, рядки 26–31

**Опис:**
Endpoints `/api/v1/schema/` та `/api/v1/redoc/` захищені лише глобальним `IsAuthenticated`. Будь-який зареєстрований мешканець може переглянути повну документацію API, включаючи admin-endpoints, параметри запитів та структуру даних — суттєве полегшення для розвідки атакуючого.

**Рекомендація:**
```python
from rest_framework.permissions import IsAdminUser
path("api/v1/schema/", SpectacularAPIView.as_view(permission_classes=[IsAdminUser]), ...),
# або додати до SPECTACULAR_SETTINGS:
SPECTACULAR_SETTINGS["SERVE_PERMISSIONS"] = ["rest_framework.permissions.IsAdminUser"]
```

---

## 🟡 Середній ризик

---

### [MED-1] Довіра до `X-Forwarded-For` без валідації — IP spoofing

**Файли:** `server/apps/issues/views.py`, рядки 335–356
`server/apps/posts/views.py`, рядки 218–232

**Опис:**
Метод `get_client_ip()` в обох файлах береться `X-Forwarded-For` без перевірки чи проксі довірений:

```python
x_forwarded_for = self.request.META.get("HTTP_X_FORWARDED_FOR")
if x_forwarded_for:
    ip = x_forwarded_for.split(",")[0].strip()
```

Клієнт може підставити довільний IP, обходячи механізм унікальних view counts та аналітику.

**PoC:**
```bash
curl -H "X-Forwarded-For: 1.2.3.4" https://api.example.com/api/v1/issues/123/
# → IP записується як 1.2.3.4 незалежно від реального IP
```

**Рекомендація:**
Використовувати `django-ipware` або довіряти `X-Forwarded-For` лише якщо запит прийшов від відомих проксі:
```python
from ipware import get_client_ip
ip, is_routable = get_client_ip(request)
```

---

### [MED-2] Передбачувана URL Admin-панелі

**Файл:** `server/config/settings/base.py`, рядок 204

**Опис:**
```python
ADMIN_URL = "django-admin/"
```
URL захищений паролем, але `django-admin/` — відомий за замовчуванням URL Django-адміністратора. Це полегшує таргетовані brute-force атаки.

**Рекомендація:**
Встановити непередбачуваний URL через env-var:
```python
ADMIN_URL = env.str("DJANGO_ADMIN_URL", default="secret-admin-panel-url/")
```

---

### [MED-3] Banned-статус не перевіряється при аутентифікації

**Файл:** `server/apps/profiles/models.py`, рядки 155–165

**Опис:**
Модель `Profile` має властивість `is_banned` (якщо `report_count >= 5`), але цей статус **не перевіряється ні при логіні, ні при кожному API-запиті**. Забанений мешканець продовжує мати повний доступ до системи.

**Рекомендація:**
Або встановлювати `user.is_active = False` при бані, або перевіряти статус у custom permission class:
```python
class IsNotBanned(BasePermission):
    def has_permission(self, request, view):
        if hasattr(request.user, 'profile') and request.user.profile.is_banned:
            return False
        return True
```

---

### [MED-4] `is_staff` прапор витікає у публічний ProfileSerializer

**Файл:** `server/apps/profiles/serializers.py`, рядок 43

**Опис:**
```python
is_staff = serializers.ReadOnlyField(source="user.is_staff")
```

Поле `is_staff` включено у `ProfileSerializer`, який використовується у публічних endpoints (`/api/v1/profiles/` — список всіх профілів). Будь-який аутентифікований користувач може визначити, хто з користувачів є адміністратором — корисна інформація для соціальної інженерії.

**Рекомендація:**
Видалити `is_staff` з `ProfileSerializer` або залишити лише для admin-serializers.

---

### [MED-5] IDOR на адмін-списку VehiclePass — guard бачить усі перепустки

**Файл:** `server/apps/passes/views.py`, рядки 32–35

**Опис:**
`VehiclePassListCreateAPIView.get_queryset()` повертає `.all()` для guard/admin без фільтрації по будівлі. Guard, призначений до одного будинку, бачить перепустки мешканців інших будинків.

```python
def get_queryset(self):
    return VehiclePass.objects.select_related(...).all()  # ← ВСІ перепустки
```

**Рекомендація:**
Фільтрувати за будівлями, якими управляє конкретний guard:
```python
if not (user.is_staff or user.is_superuser):
    managed = user.profile.buildings.all()
    if managed.exists():
        return qs.filter(unit__entrance__building__in=managed)
```

---

### [MED-6] Відсутній admin-endpoint для перегляду всіх скарг

**Файл:** `server/apps/reports/urls.py`

**Опис:**
Існують лише `create/` та `my-reports/` endpoints. Відсутній admin-endpoint для перегляду всіх скарг. Це означає, що адміністратор може переглядати звіти лише через Django Admin (/django-admin/), а не через API. Порушує принцип окремого адміністративного API.

**Рекомендація:**
Додати:
```python
path("admin/all/", ReportAdminListAPIView.as_view(), name="admin-list-reports"),
```
з `permission_classes = [IsAdminUser]`.

---

## 🟢 Добре реалізовано

---

### [GOOD-1] JWT зберігаються в httpOnly cookies (не localStorage)

**Файли:** `server/apps/users/views.py`, `client/src/utils/PersistAuth.tsx`

JWT access та refresh токени встановлюються як httpOnly cookies. Frontend зчитує лише non-httpOnly cookie `logged_in=true` для визначення стану аутентифікації. Це захищає від XSS-атак, які намагаються вкрасти токени через `document.cookie` або `localStorage`.

---

### [GOOD-2] Глобальний `IsAuthenticated` за замовчуванням

**Файл:** `server/config/settings/base.py`, рядок 279

```python
"DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
```

Всі endpoints вимагають аутентифікації якщо не визначено інакше. Правильний принцип "deny by default".

---

### [GOOD-3] Argon2 — найсильніший алгоритм хешування паролів

**Файл:** `server/config/settings/base.py`, рядки 132–137

Argon2 стоїть першим у списку `PASSWORD_HASHERS`. Переможець Password Hashing Competition 2015, стійкий до GPU та ASIC атак.

---

### [GOOD-4] Production-конфігурація безпеки повна

**Файл:** `server/config/settings/production.py`, рядки 35–41

Коректно налаштовано:
- `SECURE_SSL_REDIRECT = True`
- `SECURE_HSTS_SECONDS = 31536000` (1 рік)
- `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
- `SECURE_HSTS_PRELOAD = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`

---

### [GOOD-5] IDOR захист у Issue-endpoints

**Файл:** `server/apps/issues/views.py`, рядки 277–303

`IssueDetailAPIView.get_object()` перевіряє що лише reporter, staff або assignee може переглянути заявку. `IssueCreateAPIView` перевіряє що тенант може створювати заявки лише для свого юніту.

---

### [GOOD-6] Frontend AdminGuard + RoleGuard

**Файл:** `client/src/components/admin/AdminGuard.tsx`

Admin-panel захищена двохрівневим guard: перевірка `isAuthenticated` (Redux state) та `profile.is_staff` (API). Навіть при маніпуляції Redux-стейтом — компонент підтягує актуальні дані з API.

---

### [GOOD-7] ROTATE_REFRESH_TOKENS + секрети лише через env-vars у production

**Файл:** `server/config/settings/base.py`, рядок 316
**Файл:** `server/config/settings/production.py`, рядок 7

`ROTATE_REFRESH_TOKENS: True` забезпечує ротацію токенів при кожному оновленні. Production `SECRET_KEY` та всі credentials беруться виключно з env-vars без defaults.

---

### [GOOD-8] Frontend client-side валідація через Zod

**Директорія:** `client/src/lib/validationSchemas/`

Всі форми (register, login, issue create, profile edit, pass create) мають Zod-схеми для client-side валідації. Хоча це не замінює server-side валідацію, зменшує навантаження на backend та покращує UX.

---

## Зведена таблиця

| ID | Рівень | Категорія | Файл | Статус |
|----|--------|-----------|------|--------|
| CRIT-1 | 🔴 Критично | Secrets in Git | `.envs/.local/*.env` | Відкрито |
| CRIT-2 | 🔴 Критично | Mass Assignment / Privilege Escalation | `profiles/serializers.py:186` | Відкрито |
| CRIT-3 | 🔴 Критично | File Upload Validation | `profiles/serializers.py:234` | Відкрито |
| CRIT-4 | 🔴 Критично | JWT No Blacklist on Logout | `users/views.py:269` | Відкрито |
| HIGH-1 | 🟠 Високий | Default JWT Signing Key | `settings/base.py:313` | Відкрито |
| HIGH-2 | 🟠 Високий | Insufficient Rate Limiting | `settings/base.py:285` | Відкрито |
| HIGH-3 | 🟠 Високий | Missing CORS Config (local) | `settings/local.py` | Відкрито |
| HIGH-4 | 🟠 Високий | Hardcoded Creds in seed_demo | `seed_demo.py` | Відкрито |
| HIGH-5 | 🟠 Високий | API Docs Exposed to All Users | `config/urls.py:26` | Відкрито |
| MED-1 | 🟡 Середній | IP Spoofing via X-Forwarded-For | `issues/views.py:335` | Відкрито |
| MED-2 | 🟡 Середній | Predictable Admin URL | `settings/base.py:204` | Відкрито |
| MED-3 | 🟡 Середній | Banned User Can Still Login | `profiles/models.py:155` | Відкрито |
| MED-4 | 🟡 Середній | is_staff Leaked in Public API | `profiles/serializers.py:43` | Відкрито |
| MED-5 | 🟡 Середній | IDOR Vehicle Passes | `passes/views.py:32` | Відкрито |
| MED-6 | 🟡 Середній | No Admin Reports Endpoint | `reports/urls.py` | Відкрито |
