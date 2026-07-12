.DEFAULT_GOAL := help

.PHONY: help setup migrate makemigrations test lint format format-check run worker schema check docker-up docker-down

help:
	@echo "setup          Install locked dependencies"
	@echo "migrate        Apply database migrations"
	@echo "makemigrations Create migrations"
	@echo "test           Run backend tests with coverage"
	@echo "lint           Run Ruff checks"
	@echo "format         Format Python files"
	@echo "format-check   Verify formatting"
	@echo "run            Run development server"
	@echo "worker         Run Celery worker"
	@echo "schema         Generate and validate OpenAPI schema"
	@echo "check          Run Django deployment-independent checks"
	@echo "docker-up      Start backend infrastructure"
	@echo "docker-down    Stop backend infrastructure"

setup:
	uv sync --all-groups

migrate:
	uv run python manage.py migrate

makemigrations:
	uv run python manage.py makemigrations

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

format-check:
	uv run ruff format --check .


run:
	uv run python manage.py runserver 0.0.0.0:8000

worker:
	uv run celery -A config worker --loglevel=INFO --queues=default

schema:
	uv run python manage.py spectacular --file docs/openapi-schema.yml --validate

check:
	uv run python manage.py check
	uv run python manage.py makemigrations --check --dry-run

docker-up:
	docker compose up --build

docker-down:
	docker compose down
