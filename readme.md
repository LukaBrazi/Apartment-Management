# ОСББ / Керуюча в кишені — Alpha Apartments

Веб-портал для керування багатоквартирними будинками (ОСББ). Мешканці повідомляють про проблеми, отримують оголошення від управляючої компанії та стежать за статусом ремонтних заявок з дотриманням SLA.

## Особливості

### Автентифікація
- JWT cookie-аутентифікація
- Реєстрація та вхід за email/паролем
- Google OAuth (конфігурується)

### Ієрархія нерухомості
- **Будинок (Building)** → **Під'їзд (Entrance)** → **Квартира (Unit)**
- Зворотна сумісність із старою моделлю `Apartment`

### Заявки на обслуговування (Service Requests / Issues)
- Категорії із SLA (норматив часу виконання в годинах)
- Автоматичний розрахунок `due_at` та флаг `is_overdue`
- Чіткий потік статусів: `reported → accepted → in_progress → done | rejected`
- Email-сповіщення при вирішенні заявки

### Оголошення (Announcements)
- Оголошення прив'язані до конкретного будинку
- Мешканці бачать лише оголошення свого будинку

### Профілі та рейтинги
- Профілі мешканців і технічних спеціалістів
- Рейтингова система технічного персоналу

### Публікації (Posts)
- Стрічка публікацій з тегами, голосуванням, закладками
- Коментарі та перегляди

### Звіти про порушення (Reports)
- Перша скарга — попередження
- Після 5 скарг обліковий запис деактивується

## Технічний стек

### Backend
- **Django 4.2** + **Django REST Framework**
- **PostgreSQL** — основна СУБД
- **Celery** + **Redis** — черга задач
- **MinIO** — S3-сумісне сховище статичних і медіа-файлів
- **Mailpit** — SMTP-перехоплювач для розробки
- **pytest** + **factory_boy** — тестування

### Frontend
- **Next.js** — React-фреймворк
- **TailwindCSS** + **Heroicons**
- **Redux** — управління станом
- **Zod** — валідація даних
- **Axios** — HTTP-запити

### Інфраструктура
- **Docker Compose** — локальна оркестрація
- **Nginx** — зворотний проксі

## Швидкий старт

### Залежності
- Docker та Docker Compose

### Запуск

```bash
# Клонувати репозиторій
git clone <repo-url>
cd Django-Apartment-Management

# Запустити всі сервіси
make up

# Або вручну
docker compose -f docker-compose.local.yml up --build
```

### Після першого запуску

```bash
# Створити MinIO bucket (тільки при першому запуску)
make minio-init

# Наповнити демо-даними
make seed

# Створити суперкористувача
make createsuperuser
```

### Доступні адреси

| Сервіс | URL |
|--------|-----|
| Frontend | http://localhost:8080/ |
| Django Admin | http://localhost:8080/admin/ |
| REST API | http://localhost:8080/api/v1/ |
| Swagger UI | http://localhost:8080/swagger/redoc/ |
| MinIO Console | http://localhost:9090/ |
| Mailpit | http://localhost:8025/ |
| Flower (Celery) | http://localhost:5555/ |

### Облікові дані для розробки

| Сервіс | Логін | Пароль |
|--------|-------|--------|
| Django Admin | admin@admin.com | admin123 |
| MinIO | minioadmin | minioadmin123 |

## Тестування

```bash
# Запустити всі тести
make test

# З покриттям
make test-cov
```

## Сервіси Docker

| Сервіс | Опис |
|--------|------|
| `server` | Django backend |
| `client` | Next.js frontend |
| `postgres` | PostgreSQL база даних |
| `minio` | MinIO сховище файлів |
| `mailpit` | SMTP-перехоплювач |
| `redis` | Брокер повідомлень |
| `celeryworker` | Celery воркер |
| `celerybeat` | Celery планувальник |
| `flower` | Моніторинг Celery |
| `nginx` | Зворотний проксі |

## Ліцензія

MIT License

---

Розробник: **Andriienko Dmytro**
