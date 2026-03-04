# TODO — Alpha Apartments (ОСББ/Керуюча в кишені)

## Готово (MVP v1)

- [x] Модель Building → Entrance → Unit (ієрархія нерухомості)
- [x] Міграція даних з Apartment у Unit (backward-compat)
- [x] Категорії заявок із SLA (`sla_hours`, `due_at`, `is_overdue`)
- [x] Розширений потік статусів: `reported → accepted → in_progress → done | rejected`
- [x] Метод `transition_to()` з валідацією переходів
- [x] Email-сповіщення при вирішенні заявки
- [x] Оголошення (Announcement), прив'язані до будинку
- [x] Команда `seed_demo` (демо-дані, ідемпотентна)
- [x] Pytest + factory_boy (35+ тестів)
- [x] Serializer aliases (backward compat для старих клієнтів)
- [x] Docker Compose локальне середовище (PostgreSQL, Redis, MinIO, Mailpit, Nginx)
- [x] MinIO public-read для static/ (CSS/JS адміністратора)
- [x] Werkzeug reloader → `--reloader-type stat` (стабільний перезапуск)
- [x] README українською + Makefile

---

## Backend — що залишилось

### Критичне

- [ ] **Перейменувати `TIME_ZONE`** з `"Asia/Kolkata"` на `"Europe/Kyiv"` у `base.py`
- [ ] **Вʼязка Unit ↔ Profile**: додати FK `unit` до `Profile` (зараз мешканець «без адреси»)
- [ ] **Права доступу на заявки**: диспетчер — усі заявки свого будинку; мешканець — тільки свої
- [ ] **SLA-переходи через API**: ендпоінт `PATCH /issues/<id>/transition/` з полем `status`
- [ ] **Фільтрація та сортування заявок**: за статусом, пріоритетом, категорією, будинком, `is_overdue`

### Функціонал

- [ ] **Призначення заявки диспетчером**: `PATCH /issues/<id>/assign/` — поле `assigned_to`
- [ ] **Push / WebSocket сповіщення**: реальний час для зміни статусу заявки (Django Channels або SSE)
- [ ] **API оголошень**: `POST /posts/announcements/` (створення диспетчером), `PATCH`, `DELETE`
- [ ] **Фільтр оголошень**: активні / неактивні, за будинком
- [ ] **Завантаження фотографій до заявки**: прикріплення файлів через Media/MinIO
- [ ] **Celery task**: автоматична перевірка `is_overdue` (щогодини), сповіщення диспетчеру
- [ ] **Звіти**: PDF/Excel-вивантаження заявок за Period + Building (менеджмент-звіт)

### Якість

- [ ] **Покриття тестами ≥ 80%**: views, permissions, SLA transitions, announcements API
- [ ] **API-тести** (APIClient): POST /issues/, PATCH status, GET announcements, filtering
- [ ] **Fixture або factory для seed**: детерміновані дані для CI
- [ ] **Перевірити `makemigrations --check`** у CI (GitHub Actions)

---

## Frontend — що залишилось

- [ ] **Сторінка заявок**: фільтри по статусу / будинку, бейдж `OVERDUE`
- [ ] **Деталь заявки**: timeline статусів, кнопки переходу для диспетчера
- [ ] **Сторінка оголошень**: стрічка оголошень для мешканця
- [ ] **Форма нової заявки**: вибір Unit зі списку, категорія, пріоритет
- [ ] **Dashboard диспетчера**: лічильники (нові / прострочені / в роботі)
- [ ] **Профіль мешканця**: показ адреси (будинок/під'їзд/квартира)
- [ ] **i18n**: підтримка української мови в Next.js (next-intl або react-i18next)

---

## DevOps / Інфраструктура

- [ ] **`.env.example`**: шаблон усіх змінних оточення для нових розробників
- [ ] **GitHub Actions CI**: `pytest`, `ruff`, `mypy` при кожному PR
- [ ] **Production docker-compose**: Gunicorn + WhiteNoise або окремий nginx для static
- [ ] **Секрети**: перенести в `.envs/.production/` та документувати
- [ ] **Healthcheck** для server-контейнера в docker-compose
- [ ] **Backup скрипт** для PostgreSQL (pg_dump → MinIO)

---

## Технічний борг

- [ ] Видалити дублювання `DJANGO_SECRET_KEY` у `.django.env` (рядки 2 і 28)
- [ ] `COOKIE_SECURE` — кастомне поле; перевірити де використовується та чи потрібне
- [ ] `StaticStorage.file_overwrite = False` — повільний collectstatic; розглянути `True` для статики
- [ ] Видалити `apartment_unit` (legacy field) після переходу фронту на `unit_number`
- [ ] Замінити `apartment` FK в `IssueStatusUpdateSerializer` на `unit`
