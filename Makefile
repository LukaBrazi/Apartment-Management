

COMPOSE    = docker compose -f docker-compose.local.yml
COMPOSE_CI = docker compose -f docker-compose.ci.yml
DB_URL = postgres://alpha_user:alpha_password@postgres:5432/alpha_apartments

.PHONY: help up down restart build logs shell test test-cov migrate makemigrations \
        createsuperuser seed minio-init collectstatic celeryworker celerybeat \
        ci-up ci-down ci-seed e2e

help:
	@echo "Skandi Apartments — команди Make"
	@echo ""
	@echo "  make up              Запустити всі сервіси (foreground)"
	@echo "  make up-d            Запустити всі сервіси (background)"
	@echo "  make down            Зупинити та видалити контейнери"
	@echo "  make restart         Перезапустити всі сервіси"
	@echo "  make build           Зібрати Docker образи"
	@echo "  make logs            Показати логи всіх сервісів"
	@echo "  make logs-server     Показати логи Django сервера"
	@echo ""
	@echo "  make shell           Django shell (manage.py shell)"
	@echo "  make migrate         Застосувати міграції БД"
	@echo "  make makemigrations  Створити нові міграції"
	@echo "  make createsuperuser Створити суперкористувача"
	@echo "  make seed            Наповнити БД демо-даними"
	@echo "  make collectstatic   Зібрати статику в MinIO"
	@echo ""
	@echo "  make minio-init      Ініціалізувати MinIO bucket (перший запуск)"
	@echo ""
	@echo "  make test            Запустити тести"
	@echo "  make test-cov        Тести з покриттям коду"
	@echo ""
	@echo "  make ci-up           Підняти CI-стек (без MinIO/Mailpit/Celery)"
	@echo "  make ci-down         Зупинити CI-стек"
	@echo "  make ci-seed         Наповнити CI БД демо-даними"
	@echo "  make e2e             Запустити Playwright E2E тести (проти CI-стеку)"
	@echo ""
	@echo "  Доступні адреси після make up:"
	@echo "    http://localhost:8080        — Frontend"
	@echo "    http://localhost:8080/admin/ — Django Admin"
	@echo "    http://localhost:8080/api/v1/— REST API"
	@echo "    http://localhost:9090/       — MinIO Console"
	@echo "    http://localhost:8025/       — Mailpit"
	@echo "    http://localhost:5555/       — Flower (Celery)"

# --- Запуск ---

up: docker-start
	$(COMPOSE) up

up-d: docker-start
	$(COMPOSE) up -d

docker-start:
	@if ! docker info > /dev/null 2>&1; then \
		echo "Docker не запущений. Запускаємо Docker Desktop..."; \
		open -a Docker; \
		echo "Чекаємо поки Docker запуститься..."; \
		while ! docker info > /dev/null 2>&1; do sleep 2; done; \
		echo "Docker готовий."; \
	fi

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

logs-server:
	$(COMPOSE) logs -f server

# --- Django ---

shell:
	$(COMPOSE) exec -e DATABASE_URL=$(DB_URL) server python manage.py shell

migrate:
	$(COMPOSE) exec -e DATABASE_URL=$(DB_URL) server python manage.py migrate --no-input

makemigrations:
	$(COMPOSE) exec -e DATABASE_URL=$(DB_URL) server python manage.py makemigrations --no-input

createsuperuser:
	$(COMPOSE) exec -e DATABASE_URL=$(DB_URL) server python manage.py createsuperuser

seed:
	$(COMPOSE) exec -e DATABASE_URL=$(DB_URL) server python manage.py seed_demo

collectstatic:
	$(COMPOSE) exec -e DATABASE_URL=$(DB_URL) server python manage.py collectstatic --no-input

# --- MinIO ---

minio-init:
	@echo "Створення MinIO bucket та налаштування публічного доступу до static..."
	$(COMPOSE) exec minio mc alias set local http://localhost:9000 minioadmin minioadmin123
	$(COMPOSE) exec minio mc mb --ignore-existing local/skandi-apartments
	$(COMPOSE) exec minio mc anonymous set public local/skandi-apartments/static
	@echo "MinIO bucket готовий."

# --- Тести ---

test:
	cd server && ../.venv/bin/pytest apps/tests/ -v

test-cov:
	cd server && ../.venv/bin/pytest apps/tests/ -v --cov=apps --cov-report=term-missing

# --- CI / E2E ---

ci-up:
	$(COMPOSE_CI) up -d --build

ci-down:
	$(COMPOSE_CI) down

ci-seed:
	$(COMPOSE_CI) exec -T server python manage.py seed_demo

e2e:
	cd ../sckandi-e2e && npx playwright test --workers=1
