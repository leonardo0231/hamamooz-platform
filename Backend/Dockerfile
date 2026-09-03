FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN python -m venv /opt/venv

ARG PIP_INDEX_URL
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

COPY requirements/production.txt requirements/base.txt /tmp/requirements/
RUN /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r /tmp/requirements/production.txt

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH"

RUN sed -i \
    -e 's|http://deb.debian.org/debian-security|http://mirror-linux.runflare.com/debian-security|g' \
    -e 's|http://deb.debian.org/debian|http://mirror-linux.runflare.com/debian|g' \
    /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        fonts-dejavu-core \
        libjpeg62-turbo \
        libopenjp2-7 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libpq5 \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 hamamooz \
    && useradd --system --uid 10001 --gid hamamooz --home-dir /app --shell /usr/sbin/nologin hamamooz

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY . /app
RUN chmod +x /app/scripts/*.sh \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R hamamooz:hamamooz /app

USER hamamooz

EXPOSE 8000
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "120", "--access-logfile", "-"]
