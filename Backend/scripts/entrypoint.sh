#!/bin/sh
set -eu

# Root Compose can run without a .env file. Build DATABASE_URL from the same
# PostgreSQL variables used by the database service unless an explicit URL was
# supplied. For passwords containing URL-reserved characters, set DATABASE_URL
# explicitly with a URL-encoded password.
if [ -z "${DATABASE_URL:-}" ]; then
    export DATABASE_URL="postgresql://${POSTGRES_USER:-hamamooz}:${POSTGRES_PASSWORD:-hamamooz-local-password}@${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-hamamooz}"
fi

exec "$@"
