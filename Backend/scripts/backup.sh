#!/usr/bin/env bash

set -Eeuo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"
BACKUP_ROOT="${BACKUP_ROOT:-./backups}"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
snapshot_dir="${BACKUP_ROOT}/${timestamp}"
archive="${BACKUP_ROOT}/hamamooz-${timestamp}.tar.gz"

mkdir -p "${snapshot_dir}/minio"

compose=(
  docker compose
  --env-file "${ENV_FILE}"
  -f "${COMPOSE_FILE}"
)

"${compose[@]}" exec -T postgres \
  sh -ec '
    PGPASSWORD="$POSTGRES_PASSWORD" \
    pg_dump \
      --username "$POSTGRES_USER" \
      --dbname "$POSTGRES_DB" \
      --format custom \
      --no-owner \
      --no-acl
  ' > "${snapshot_dir}/postgres.dump"

BACKUP_WORKDIR="${snapshot_dir}" \
"${compose[@]}" \
  --profile ops \
  run --rm minio-client '
    mc alias set \
      source \
      http://minio:9000 \
      "$MINIO_ROOT_USER" \
      "$MINIO_ROOT_PASSWORD"

    mc mirror \
      --overwrite \
      "source/$AWS_STORAGE_BUCKET_NAME" \
      /backup/minio
  '

tar \
  -C "${snapshot_dir}" \
  -czf "${archive}" \
  .

sha256sum "${archive}" \
  > "${archive}.sha256"

if [[ -n "${BACKUP_ENCRYPTION_KEY:-}" ]]; then
  openssl enc \
    -aes-256-cbc \
    -salt \
    -pbkdf2 \
    -iter 200000 \
    -in "${archive}" \
    -out "${archive}.enc" \
    -pass env:BACKUP_ENCRYPTION_KEY

  sha256sum "${archive}.enc" \
    > "${archive}.enc.sha256"

  rm -f "${archive}"
fi

rm -rf "${snapshot_dir}"

echo "Backup completed: ${archive}"