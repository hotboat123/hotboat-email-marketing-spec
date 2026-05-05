.PHONY: dev dev-db dev-api dev-frontend install migrate seed help

help:
	@echo "Comandos disponibles:"
	@echo "  make dev          — Levanta todo con Docker Compose"
	@echo "  make dev-db       — Solo la base de datos (Postgres)"
	@echo "  make dev-api      — API FastAPI en local (requiere .env)"
	@echo "  make dev-frontend — Frontend Next.js en local"
	@echo "  make install      — Instala dependencias frontend"
	@echo "  make migrate      — Genera y aplica migraciones Alembic"

dev:
	docker compose up --build

dev-db:
	docker compose up db

dev-api:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

install:
	cd frontend && npm install
	cd backend && pip install -r requirements.txt

migrate:
	cd backend && alembic revision --autogenerate -m "$(msg)" && alembic upgrade head
