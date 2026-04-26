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

Покрокова інструкція deploy/troubleshoot — `docs/RAILWAY_SETUP.md`.

### Git з Linux sandbox (важливо)

- macOS APFS не дозволяє Linux sandbox видаляти `.git/index.lock` після git операцій.
- **Ніколи не запускати `git add` / `git commit` / `git push` зі sandbox** — залишається index.lock і наступні команди падають.
- Натомість: підготувати список файлів і команди → передати Dmytro для виконання з Mac терміналу.
- Якщо index.lock завис: `rm ~/PycharmProjects/Django-Apartment-Management/.git/index.lock`

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
