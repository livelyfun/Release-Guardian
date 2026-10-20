.PHONY: help install install-backend install-frontend up down migrate revision dev-api dev-worker dev-scheduler dev-web test lint format check load-test drill-backup drill-resilience security-scan cost-model

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

help:
	@echo "Targets:"
	@echo "  install           Install backend and frontend dependencies"
	@echo "  up / down         Start / stop local Postgres and Redis"
	@echo "  migrate           Apply Alembic migrations"
	@echo "  revision          Create an Alembic revision (m=\"message\")"
	@echo "  dev-api           Run FastAPI with reload"
	@echo "  dev-worker        Run the Celery worker"
	@echo "  dev-scheduler     Run the Celery beat scheduler"
	@echo "  dev-web           Run the Next.js dev server"
	@echo "  test              Run backend tests"
	@echo "  lint / format     Lint / format backend"
	@echo "  check             Lint, test, and build frontend"
	@echo "  load-test         Run the local load test (API on :8010 required)"
	@echo "  drill-backup      Run the Postgres backup/restore drill"
	@echo "  drill-resilience  Stop/start the worker during a queued run"
	@echo "  security-scan     Scan environment/config for exposed secrets"
	@echo "  cost-model        Print the illustrative monthly cost model"

install: install-backend install-frontend

install-backend:
	$(PIP) install -r backend/requirements.txt -r backend/requirements-dev.txt

install-frontend:
	cd frontend && npm install

up:
	docker compose up -d postgres redis

down:
	docker compose down

migrate:
	cd backend && alembic upgrade head

revision:
	cd backend && alembic revision --autogenerate -m "$(m)"

dev-api:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-worker:
	cd backend && celery -A app.workers.celery_app.celery_app worker --loglevel=info

dev-scheduler:
	cd backend && celery -A app.workers.celery_app.celery_app beat --loglevel=info

dev-web:
	cd frontend && npm run dev

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint

format:
	cd backend && ruff format app tests

check: lint test
	cd frontend && npm run build

load-test:
	$(PYTHON) scripts/load_test.py --start-fixture

drill-backup:
	scripts/backup_restore_drill.sh

drill-resilience:
	$(PYTHON) scripts/resilience_drill.py

security-scan:
	cd backend && .venv/bin/python -m app.services.secret_scanner

cost-model:
	$(PYTHON) scripts/cost_model.py
