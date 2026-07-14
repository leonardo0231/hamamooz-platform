.PHONY: dev test lint format migrate makemigrations seed templates schema check backup

dev:
	python manage.py runserver

test:
	pytest --cov=hamamooz --cov-report=term-missing

lint:
	ruff check .

format:
	ruff check --fix .
	ruff format .

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

seed:
	python manage.py seed_demo

templates:
	python manage.py generate_import_templates

schema:
	python manage.py spectacular --api-version v1 --file openapi.yaml --validate

check:
	python manage.py check --deploy

backup:
	./scripts/backup_postgres.sh
