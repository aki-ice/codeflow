.PHONY: install dev test lint format migrate docker-build docker-up docker-down

install:
	uv sync --all-packages

# 本地全栈（需要先 docker compose up -d postgres redis kafka）
dev-user:
	uv run uvicorn user_service.main:app --reload --port 8001 --project services/user-service
dev-project:
	uv run uvicorn project_service.main:app --reload --port 8002 --project services/project-service
dev-notification:
	uv run uvicorn notification_service.main:app --reload --port 8003 --project services/notification-service
dev-gateway:
	uv run uvicorn gateway_service.main:app --reload --port 8000 --project services/gateway-service

test:
	uv run pytest services

lint:
	uv run ruff check services libs
	uv run mypy libs/common services

format:
	uv run ruff format services libs
	uv run ruff check --fix services libs

migrate:
	cd services/user-service && uv run --project . alembic upgrade head
	cd services/project-service && uv run --project . alembic upgrade head
	cd services/notification-service && uv run --project . alembic upgrade head

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
