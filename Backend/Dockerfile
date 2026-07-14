<<<<<<< HEAD
FROM python:3.12-slim-bookworm AS runtime
=======
# syntax=docker/dockerfile:1.7

FROM python:3.13-slim-bookworm AS runtime
>>>>>>> d1ab717a752428a109c9478b838e8338dccd9265

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

<<<<<<< HEAD
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    fonts-dejavu-core \
    libjpeg62-turbo \
    libopenjp2-7 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpq5 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements/production.txt requirements/base.txt /app/requirements/
RUN pip install --upgrade pip && pip install -r requirements/production.txt

COPY . /app
RUN chmod +x /app/scripts/*.sh && mkdir -p /app/media /app/staticfiles

EXPOSE 8000
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "120", "--access-logfile", "-"]
=======
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libjpeg62-turbo \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /uvx /bin/

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

CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
>>>>>>> d1ab717a752428a109c9478b838e8338dccd9265
