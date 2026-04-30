# ApartmentOS — Project Instructions

## Git & Deployment Rules

### Push to main — ЗАБОРОНЕНО без дозволу

**Тільки CEO (Dmytro) має право пушити в `main`.**

- Без прямої команди або спеціальної вказівки — **НЕ пушити в main**.
- Усі зміни оформлюються через feature-гілку → PR → code review → merge CEO.
- Агенти можуть комітити у feature-гілки, але push в `main` — виключно з дозволу CEO.
- Якщо потрібно терміново пушнути — запитай дозвіл у CEO перед push.
- Ніколи не робити репо публічним.

**Direct-merge батчі (CEO authorized):** для великих cleanup/refactor batch'ів CEO
може дати разовий дозвіл на pattern: feature branch → push → ff-merge до main →
push origin main, **без GitHub PR review**. Тоді кожен PR отримує власний
`MERGE-PR{N}.sh` скрипт що CEO запускає на Mac terminal. Скрипт виключає
сам себе з commit (`git reset HEAD MERGE-*.sh`). Дозвіл діє тільки на ту
конкретну розмову — повертайся до PR review за замовчуванням.

### CI/CD

- Railway "Wait for CI" увімкнено — деплой тільки після зелених тестів.
- GitHub Actions: Django pytest → Playwright E2E → auto-deploy.
- **Dependabot** активний (npm + pip + actions, weekly Mon Europe/Kiev).
  Гілки `dependabot/*` потребують ручного triage перед merge.
- **Security scan** — `pip-audit` + `npm audit` у CI з `continue-on-error: true`.
  Findings йдуть у `docs/SECURITY_BACKLOG.md` для розгрібання.

### Railway deploy — multi-service setup

ApartmentOS на Railway = 3 окремих сервіси (Web, Celery Worker, Celery Beat).
**Кожен сервіс має свою конфігурацію в Railway dashboard.** `healthcheckPath`
у root `railway.toml` ЗАБОРОНЕНО — він поширюється на всі 3 сервіси і
ламає Celery deploys ("service unavailable"). Lock-down тест
`apps/tests/test_railway_config.py` стереже це правило.

**Per-service env vars (gotcha з 2026-04-29):** Web і Celery Worker — окремі
сервіси, кожен має СВІЙ набір env vars. Якщо змінна потрібна на обох
(наприклад `RESEND_API_KEY`, `ERROR_ALERTS_TG_*`, `TOS_VERSION`) — додавай
на ОБИДВА. Альтернативно, можна використати Railway shared variable
reference `${{<source-service>.VAR_NAME}}` щоб не дублювати значення.

Покрокова інструкція deploy/troubleshoot — `docs/RAILWAY_SETUP.md`.

### Railway deploy debugging (lessons learned 2026-04-29 wave 2)

При застряглих deploys пам'ятай в такому порядку:

1. **`status.railway.app` — ПЕРШИЙ крок** діагностики stuck deploys >5 хв.
   2026-04-29 ввечері Railway мав incident "Image Registry (Metal) — Investigating",
   через що 4 сервіси висіли у `Queued (Processing deployment...)` з усіма
   sub-stages "Not started". Не наш код, не наш CI — їх інфра. Чекаємо
   resolved status замість того щоб гадати на код.

2. **"Redeploy" ≠ "deploy latest commit".** Натиснення Redeploy на ACTIVE
   deploy redeployить **той самий commit**, що зараз active, не новіший
   commit з main. Воспроизведено: натиснули Redeploy очікуючи що PR-14
   піднімется → Railway re-deployив PR-13a era code, PR-14 не задеплоївся.

3. **Force redeploy від latest main = empty commit pattern:**
   ```bash
   git commit --allow-empty -m "ci: force Railway redeploy"
   git push origin main
   ```
   Railway отримує webhook на новий commit hash → робить fresh build з усім
   останнім main кодом. Працює коли redeploy зависає або підхоплює старий
   commit.

4. **Webhook іноді не доходить.** Якщо після push на main у Railway
   Deployments tab не з'являється новий entry за 30 секунд — webhook
   пропустився (буває). Empty commit + push зазвичай вирішує (різний hash —
   точно triggerне новий webhook).

5. **Concurrent build cap.** На малих планах Railway паралельні builds
   обмежені. Якщо у Deployments tab бачиш кілька QUEUED одного сервісу —
   Cancel старі (`⋮ → Cancel`) щоб не блокували slot для свіжого. Перевір
   `railway.app/account/usage` для лімітів.

6. **ВСІ 4 сервіси треба redeploy** окремо (BE, FE, Celery, Celery beat) —
   Railway тригерить webhook на кожен сервіс паралельно, але не атомарно.
   Якщо 1 завис — інші можуть deployити нормально, утворюючи split state
   (BE на новому коді, FE на старому). Перевіряй що в кожному з 4-х
   сервісів latest deploy = ACTIVE, не QUEUED.

### Email backend — Resend HTTP API only (без SMTP)

**Railway egress блокує/затримує SMTP** (підтверджено експериментально:
`smtp.resend.com:587` і `:465` обидва timeout-ять). Тому використовуємо
**Resend HTTP API** через custom backend `apps.common.email_backends.ResendEmailBackend`.

Архітектура (PR-12):
- `EMAIL_BACKEND = "djcelery_email.backends.CeleryEmailBackend"` — top-level
  (Django writer) — кладе на Celery queue
- `CELERY_EMAIL_BACKEND = "apps.common.email_backends.ResendEmailBackend"` —
  worker-side, дзвонить `resend.Emails.send(payload)` через офіційний
  Python SDK (без anymail обгортки)
- Conditional у `production.py`: якщо `RESEND_API_KEY` порожній → SMTP
  fallback (для dev/CI/staging без Resend)

Setup: `RESEND_API_KEY` env var має бути на ОБОХ Web і Celery Worker
сервісах. Без нього на Worker — fallback до SMTP → timeout.

Verified domain: `apartmentos.org` у Resend → `noreply@apartmentos.org`
як `DEFAULT_FROM_EMAIL`. Для тестів `onboarding@resend.dev` теж працює.

### Git з Linux sandbox (важливо)

- macOS APFS не дозволяє Linux sandbox видаляти `.git/index.lock` після git операцій.
- **Ніколи не запускати `git add` / `git commit` / `git push` зі sandbox** — залишається index.lock і наступні команди падають.
- Натомість: підготувати список файлів і команди → передати Dmytro для виконання з Mac терміналу.
- Якщо index.lock завис: `rm ~/PycharmProjects/Django-Apartment-Management/.git/index.lock`

### Merge-script gotchas (lessons learned 2026-04-29)

При написанні `MERGE-PR{N}.sh` direct-merge скриптів:

- **❌ НЕ використовуй heredoc у subshell для commit messages:**
  ```bash
  git commit -m "..." -m "$(cat <<'EOF' ... EOF)"  # ламається на апострофах!
  ```
  `<<'EOF'` всередині `$()` re-парситься bash'ем. Якщо у тілі є `won't`,
  `Telegram's`, `dedup'd` — bash шукає закриваючий `'`, не знаходить,
  падає `unexpected EOF while looking for matching '`. Воспроизведено двічі
  (PR-1, PR-9).

- **✅ Використовуй temp file pattern:**
  ```bash
  COMMIT_MSG_FILE="$(mktemp -t pr-msg)"
  trap 'rm -f "$COMMIT_MSG_FILE"' EXIT
  cat > "$COMMIT_MSG_FILE" <<COMMIT_END
  Implements: ...
  Будь-які 'апострофи', cron-таблиці, всякі дрібниці — без проблем.
  COMMIT_END
  git commit -F "$COMMIT_MSG_FILE"
  ```

- **Multi-path pytest fallback** — на Mac за замовчуванням нема `python`,
  тільки `python3`. Скрипт має пробувати `.venv/bin/pytest`, потім
  `~/.local/bin/pytest`, потім `command -v pytest`, потім
  `python3 -m pytest`. Якщо нічого нема — попередити, не падати.

- **Stale `__pycache__` після major refactor** — Python інколи не
  інвалідує `.pyc` після швидких послідовних правок (mtime collision).
  Симптом: `ModuleNotFoundError` для модуля що вже видалений з settings.
  Fix у скрипті:
  ```bash
  find "$REPO_ROOT/server" -type d -name __pycache__ -exec rm -rf {} +
  ```

- **Self-exclude скрипту** — додай у скрипт:
  ```bash
  git add -A
  git reset HEAD MERGE-PR{N}.sh 2>/dev/null || true
  git reset HEAD DEV_PLAN.md 2>/dev/null || true
  ```
  Інакше скрипт сам потрапляє у commit (було у PR-1, прибирали окремо).

## Project Structure

- **Backend:** Django + DRF (`server/`)
- **Frontend:** Next.js 14 App Router (`client/`)
- **E2E Tests:** Playwright (окремий репо `sckandi-e2e`) — **наразі не потрібні, пропускати у планах розробки**
- **Domain:** apartmentos.org

## Naming

- Бренд: **ApartmentOS** (не "Skandi Apartments", не "EstateOS")
- Реєстрація користувачів — тільки через адміна (self-registration вимкнена)
- Google OAuth — вимкнений

## AI Model Policy

Завжди використовувати **найрозумнішу та найпотужнішу доступну модель** (наприклад, `claude-opus-4` або найновішу flagship-модель Anthropic). Не використовувати легші/дешевші моделі для економії — якість важливіша.

## TDD Policy

**Весь новий код пишеться за методологією TDD (Test-Driven Development):**

1. **Red** — спочатку написати тест, який падає
2. **Green** — написати мінімальний код щоб тест пройшов
3. **Refactor** — покращити код не ламаючи тести

Правила:
- Жодного production-коду без попереднього тесту
- Тести пишуться до або паралельно з кодом — ніколи після
- PR без тестів для нового функціоналу — не мержиться
- Агенти (zhukuymosya) завжди включають написання тестів як окремий крок у плані

### Lock-down regex tests (паттерн з 2026-04-26)

Для config файлів (`railway.toml`, `next.config.mjs`, `production.py`) та
змін що неможливо повноцінно покрити рантайм-тестом — пишемо **regex-based
тести що читають файл як текст** і перевіряють критичні рядки. Приклади:

- `apps/tests/test_railway_config.py` — `healthcheckPath` НЕ в root toml
- `apps/common/tests/test_security_headers.py` — CSP block у `next.config.mjs`
- `apps/common/tests/test_logging_config.py` — JsonFormatter в `production.py`
- `apps/common/tests/test_health.py::test_production_settings_exempts_health_from_ssl_redirect` — SECURE_REDIRECT_EXEMPT регекс

Lock-down тести унеможливлюють regression на critical config через
звичайний rebase/refactor.

### Multi-tenant FK auto-pinning pattern (PR-14, 2026-04-29)

Bug 1 у PR-14 був класичним: `BuildingSerializer.Meta.fields` НЕ містив
`organization`, view не override-ив `perform_create` → `Building` зберігався
з `organization=None` → з `get_queryset` фільтром по orgs, новий запис
**миттєво зникав** для creator-staff. Симптом: "створив, побачив success,
але у списку нема". Для CEO superuser була друга маска: `get_queryset`
для superuser'а повертає все, тому bug ховався у CI з `AdminUserFactory(is_superuser=True)`.

**Правильний паттерн для будь-якого нового tenant-scoped resource:**

1. **Не додавай tenant FK у `Meta.fields`** — інакше staff може spoofити
   payload і запарковати запис у чужу org.
2. **Pin org через `perform_create`** на view:
   ```python
   def perform_create(self, serializer):
       org = _resolve_caller_organization(self.request.user)
       serializer.save(organization=org)
   ```
3. **`_resolve_caller_organization` helper** (у `apartments/views.py:44`)
   обробляє три кейси:
   - superuser з orgs → first org
   - superuser БЕЗ orgs → `None` (legacy compat для тестових fixtures)
   - staff БЕЗ orgs → `ValidationError` (інакше створений запис буде
     невидимий)
4. **Lock-down regex test** — окремо stere що organization НЕ writable
   у серіалізаторі та що `perform_create` override присутній (приклад:
   `apps/apartments/tests/test_admin_view_lockdowns.py`).
5. **Legacy endpoints теж фікси.** Якщо у проекті є дублі (новий
   `/admin/` + legacy `/create/`) — fix на обох. Frontend міг лишатися
   на legacy.
6. **Bug 1-style діагностика:** перший крок — Django Admin фільтр
   `?organization__isnull=true` на постраждалій моделі. Якщо там нові
   записи з `org=NULL` — bug підтверджено. Manual fix: пройтися по
   списку, виставити org. Або написати `python manage.py
   backfill_<model>_orgs` management command.

### TOCTOU race protection для unique_together (PR-14 pattern)

При nested create або PATCH-rename що чіпає `unique_together(parent, name)`,
оптимістична `.exists()` перед `.create()` має race window. У pre-check
все чисто, потім інший request встигає створити те ж саме → `IntegrityError`
бабахне 500. Стандартний guard:

```python
try:
    with transaction.atomic():
        instance = Model.objects.create(**data)
        # nested children тут — все під одним atomic
except IntegrityError:
    raise serializers.ValidationError(
        {"field": "Дублікат — запис уже існує."}
    )
```

`bulk_create` у тому ж `atomic` для масових children (>100 рядків) —
наприклад 500 Unit'ів на entrance — економить ~10x latency проти
per-row save() і безпечно rollback-иться як одне ціле.

## Development Workflow

Кожен раз коли надходить задача на розробку (нова фіча, фікс, рефакторинг):

1. **Prompt Validator** — запустити скіл `prompt-validator` перед початком роботи.
   - Якщо промпт можна покращити — запропонувати покращену версію і дочекатися підтвердження.
   - Якщо промпт чіткий — одразу перейти до п.2.
2. **Розбити на пункти** — задача розбивається на конкретні підзадачі.
3. **Створити план** — файл `DEV_PLAN.md` у корені проєкту з чекбоксами:
   ```markdown
   # Dev Plan: <назва задачі>
   - [ ] Крок 1
   - [ ] Крок 2
   ...
   ```
4. **Виконати** — команда (zhukuymosya або інший агент) виконує пункти по черзі, відмічає `[x]`.
5. **Після merge в main** — видалити `DEV_PLAN.md` з репо.

## End-of-Session Protocol

Коли Dmytro каже **"на сьогодні все"** (або "все на сьогодні", "закінчуємо", "до завтра"):

1. **Переглянь розмову** — визнач що важливого відбулось: нові конвенції, виправлені баги, змінена архітектура, нові правила, оновлені API routes, нові seed дані, тощо.
2. **Оновити `CLAUDE.md`** (цей файл) — якщо з'явились нові правила, важливі рішення або зміни в архітектурі яких тут ще немає.
3. **Оновити `client/CLAUDE.md`** — якщо змінились API routes, селектори, seed users, відомі gotchas або технічні конвенції.
4. **Оновити скіли** — якщо змінились промпти агентів, структура проекту або workflow. Переупакувати `.skill` файл і презентувати через `present_files`.
5. **Якщо нічого важливого не змінилось** — просто підтвердити: "Файли актуальні, нічого критичного не змінилось."

Не оновлювати заради оновлення — тільки якщо є реальні зміни.
