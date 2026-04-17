




COMPOSE    = docker compose -f docker-compose.local.yml
COMPOSE_CI = docker compose -f docker-compose.ci.yml
DB_URL = postgres://alpha_user:alpha_password@postgres:5432/alpha_apartments

.PHONY: help up down restart build logs shell test test-cov migrate makemigrations \
        createsuperuser seed minio-init collectstatic celeryworker celerybeat \
        ci-up ci-down ci-clean ci-seed ci-reseed e2e e2e-ui e2e-full e2e-dev \
        fresh docker-start

help:
	@echo "ApartmentOS — команди Make"
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
	@echo "  make test            Запустити всі тести (apps/tests + organizations/tests)"
	@echo "  make test-cov        Всі тести з покриттям коду"
	@echo ""
	@echo "  ПРИМІТКА: pytest автоматично знаходить тести в apps/tests та apps/organizations/tests"
	@echo ""
	@echo "  make ci-up           Підняти CI-стек (без MinIO/Mailpit/Celery)"
	@echo "  make ci-down         Зупинити CI-стек"
	@echo "  make ci-clean        Зупинити CI-стек і видалити volumes (потрібно перед e2e-full)"
	@echo "  make ci-seed         Наповнити CI БД демо-даними"
	@echo "  make ci-reseed       Скинути і переналити демо-дані в CI БД"
	@echo "  make e2e             Запустити Playwright E2E тести (проти CI-стеку)"
	@echo "  make e2e-ui          Playwright у режимі UI (покрокова відладка)"
	@echo "  make e2e-full        Підняти стек + seed + тести + прибрати"
	@echo "  make e2e-dev         Підняти стек + seed + тести (стек залишається)"
	@echo ""
	@echo "  make fresh           Повний перезапуск: down→build→up→migrate→flush→seed→static"
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

# --- Повний перезапуск ---

fresh: docker-start
	@echo "🔴 [1/8] Зупиняємо контейнери і видаляємо volumes..."
	$(COMPOSE) down -v --remove-orphans
	@echo "🔨 [2/8] Збираємо образи..."
	$(COMPOSE) build
	@echo "🚀 [3/8] Піднімаємо інфраструктуру (postgres, redis, minio, mailpit)..."
	$(COMPOSE) up -d postgres redis minio mailpit
	@echo "⏳ [4/8] Чекаємо готовності postgres..."
	@STATUS=""; \
	for i in $$(seq 1 60); do \
		STATUS=$$(docker inspect --format='{{.State.Health.Status}}' \
		  $$($(COMPOSE) ps -q postgres) 2>/dev/null || echo "unknown"); \
		[ "$$STATUS" = "healthy" ] && echo "   ✓ postgres готовий!" && break; \
		echo "   $$i/60 — postgres: $$STATUS"; sleep 2; \
	done; \
	if [ "$$STATUS" != "healthy" ]; then \
		echo "❌ postgres не запустився"; \
		$(COMPOSE) logs postgres | tail -30; exit 1; \
	fi
	@echo "⏳ [5/8] Чекаємо готовності MinIO..."
	@STATUS=""; \
	for i in $$(seq 1 60); do \
		STATUS=$$(docker inspect --format='{{.State.Health.Status}}' \
		  $$($(COMPOSE) ps -q minio) 2>/dev/null || echo "unknown"); \
		[ "$$STATUS" = "healthy" ] && echo "   ✓ minio готовий!" && break; \
		echo "   $$i/60 — minio: $$STATUS"; sleep 2; \
	done; \
	if [ "$$STATUS" != "healthy" ]; then \
		echo "❌ minio не запустився"; \
		$(COMPOSE) logs minio | tail -30; exit 1; \
	fi
	@echo "🪣 [6/8] Створюємо MinIO bucket ДО старту сервера..."
	$(COMPOSE) exec -T minio mc alias set local http://localhost:9000 minioadmin minioadmin123
	$(COMPOSE) exec -T minio mc mb --ignore-existing local/skandi-apartments
	$(COMPOSE) exec -T minio mc anonymous set public local/skandi-apartments/static
	@echo "🚀 [7/8] Піднімаємо сервер та інші сервіси..."
	$(COMPOSE) up -d
	@echo "⏳ Чекаємо готовності сервера..."
	@STATUS=""; \
	for i in $$(seq 1 60); do \
		STATUS=$$(docker inspect --format='{{.State.Health.Status}}' \
		  $$($(COMPOSE) ps -q server) 2>/dev/null || echo "unknown"); \
		[ "$$STATUS" = "healthy" ] && echo "   ✓ server готовий!" && break; \
		echo "   $$i/60 — server: $$STATUS"; sleep 3; \
	done; \
	if [ "$$STATUS" != "healthy" ]; then \
		echo "❌ server не запустився"; \
		$(COMPOSE) logs server | tail -50; exit 1; \
	fi
	@echo "🗄️  [8/8] Міграції + flush + seed..."
	$(COMPOSE) exec -T -e DATABASE_URL=$(DB_URL) server python manage.py migrate --no-input
	$(COMPOSE) exec -T -e DATABASE_URL=$(DB_URL) server python manage.py flush --no-input
	$(COMPOSE) exec -T -e DATABASE_URL=$(DB_URL) server python manage.py seed_demo
	@echo ""
	@echo "✅ Готово! Все оновлено з нуля."
	@echo "   http://localhost:8080"

# --- Тести ---

test:
	cd server && ../.venv/bin/pytest -v

test-cov:
	cd server && ../.venv/bin/pytest -v --cov=apps --cov-report=term-missing

# --- CI / E2E ---

ci-up:
	$(COMPOSE_CI) up -d --build

ci-down:
	$(COMPOSE_CI) down

ci-clean:
	$(COMPOSE_CI) down -v --remove-orphans

ci-seed:
	$(COMPOSE_CI) exec -T server python manage.py seed_demo

ci-reseed:
	$(COMPOSE_CI) exec -T server python manage.py flush --no-input
	$(COMPOSE_CI) exec -T server python manage.py migrate --no-input
	$(COMPOSE_CI) exec -T server python manage.py seed_demo

e2e:
	cd ../sckandi-e2e && npx playwright test --workers=1

e2e-ui:
	cd ../sckandi-e2e && npx playwright test --ui

# Повний цикл: прибрати попередній стек → підняти → seed → тести → прибрати
e2e-full:
	$(MAKE) ci-clean
	$(MAKE) ci-up
	@echo "Чекаємо готовності сервера..."
	@STATUS=""; \
	for i in $$(seq 1 60); do \
		STATUS=$$(docker inspect --format='{{.State.Health.Status}}' \
		  $$($(COMPOSE_CI) ps -q server) 2>/dev/null || echo "unknown"); \
		[ "$$STATUS" = "healthy" ] && echo "Сервер готовий!" && break; \
		echo "  $$i/60 — $$STATUS"; sleep 5; \
	done; \
	if [ "$$STATUS" != "healthy" ]; then \
		echo "Сервер не запустився за відведений час (статус: $$STATUS)"; \
		$(MAKE) ci-clean; exit 1; \
	fi
	$(MAKE) ci-seed
	cd ../sckandi-e2e && npx playwright test --workers=1; E2E_EXIT=$$?; \
	  $(MAKE) ci-clean; exit $$E2E_EXIT

# Розробницький цикл: підняти → seed → тести (стек залишається для повторних запусків)
# При першому запуску використовуй `make ci-clean` перед цим, якщо є старі volume
e2e-dev:
	$(MAKE) ci-up
	@echo "Чекаємо готовності сервера..."
	@STATUS=""; \
	for i in $$(seq 1 60); do \
		STATUS=$$(docker inspect --format='{{.State.Health.Status}}' \
		  $$($(COMPOSE_CI) ps -q server) 2>/dev/null || echo "unknown"); \
		[ "$$STATUS" = "healthy" ] && echo "Сервер готовий!" && break; \
		echo "  $$i/60 — $$STATUS"; sleep 5; \
	done; \
	if [ "$$STATUS" != "healthy" ]; then \
		echo "Сервер не запустився за відведений час (статус: $$STATUS)"; exit 1; \
	fi
	$(MAKE) ci-reseed
	cd ../sckandi-e2e && npx playwright test --workers=1
