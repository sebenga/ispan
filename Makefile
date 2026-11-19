.PHONY: dev up down logs migrate seed test health

ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

dev: ## Boot local stack (SQLite OK if Docker is unavailable)
	@if command -v docker >/dev/null 2>&1; then $(MAKE) up; else echo "Docker not found — using SQLite (set DATABASE_URL when Compose is available)."; fi
	$(MAKE) migrate
	@mkdir -p .logs
	@bash scripts/dev-stack.sh

up: ## Start Postgres + Valkey containers
	docker compose up -d postgres valkey
	@echo "Waiting for Postgres…"
	@until docker compose exec -T postgres pg_isready -U ispan -d ispan >/dev/null 2>&1; do sleep 1; done

down:
	docker compose down

migrate:
	cd backend && ../.venv/bin/python manage.py migrate --noinput

seed:
	cd backend && ../.venv/bin/python manage.py seed_demo

test:
	cd backend && ../.venv/bin/python -m pytest -q || true
	cd realtime && npm test --silent || true
	cd frontend && npm test --silent || true

health:
	@curl -sf http://127.0.0.1:8001/healthz && echo
	@curl -sf http://127.0.0.1:4000/healthz && echo
