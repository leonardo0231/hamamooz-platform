# syntax=docker/dockerfile:1.7

FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libjpeg62-turbo \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.8.14 \
    /uv \
    /uvx \
    /bin/

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./

RUN uv sync \
    --frozen \
    --no-dev \
    --no-install-project

COPY manage.py ./
COPY config ./config
COPY apps ./apps

RUN uv sync \
    --frozen \
    --no-dev \
    && DJANGO_SETTINGS_MODULE=config.settings.base \
       DJANGO_SECRET_KEY=build-only-secret-not-used-at-runtime \
       JWT_SIGNING_KEY=build-only-jwt-key-not-used-at-runtime \
       USE_S3=false \
       uv run python manage.py collectstatic --noinput

RUN useradd \
    --create-home \
    --uid 10001 \
    appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD [
    "uv",
    "run",
    "gunicorn",
    "config.wsgi:application",
    "--bind",
    "0.0.0.0:8000",
    "--workers",
    "3",
    "--timeout",
    "120"
]