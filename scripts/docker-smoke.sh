#!/usr/bin/env sh
set -eu

FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"

docker compose config >/dev/null
docker compose up --build -d

attempt=0
while [ "$attempt" -lt 90 ]; do
  if curl -fsS "$FRONTEND_URL/healthz" >/dev/null 2>&1 \
    && curl -fsS "$FRONTEND_URL/api/v1/health/ready/" >/dev/null 2>&1; then
    echo "HamAmoz stack is ready: $FRONTEND_URL"
    echo "Local login: admin / Admin123!ChangeMe"
    docker compose ps
    exit 0
  fi
  attempt=$((attempt + 1))
  sleep 2
done

echo "Stack did not become ready in time." >&2
docker compose ps >&2
docker compose logs --tail=120 release bootstrap web frontend db redis-cache redis-broker >&2
exit 1
