#!/usr/bin/env bash

set -Eeuo pipefail

if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Set CONFIRM_RESTORE=YES."
  exit 1
fi

archive="${1:?Backup archive is required}"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"
RESTORE_DATABASE="${RESTORE_DATABASE:-hamamooz_restore}"
RESTORE_BUCKET="${RESTORE_BUCKET:-hamamooz-media-restore}"

workdir="$(mktemp -d)"

trap 'rm -rf "$workdir"' EXIT

if [[ "${archive}" == *.enc ]]; then
  : "${BACKUP_ENCRYPTION_KEY:?Encryption key is required}"

  openssl enc \
    -d \
    -aes-256-cbc \
    -pbkdf2 \
    -iter 200000 \
    -in "${archive}" \
    -out "${workdir}/backup.tar.gz" \
    -pass env:BACKUP_ENCRYPTION_KEY
else
  cp "${archive}" "${workdir}/backup.tar.gz"
fi

mkdir -p "${workdir}/snapshot"

tar \
  -C "${workdir}/snapshot" \
  -xzf "${workdir}/backup.tar.gz"

compose=(
  docker compose
  --env-file "${ENV_FILE}"
  -f "${COMPOSE_FILE}"
)

"${compose[@]}" exec -T \
  -e RESTORE_DATABASE="${RESTORE_DATABASE}" \
  postgres \
  sh -ec '
    export PGPASSWORD="$POSTGRES_PASSWORD"

    dropdb \
      --if-exists \
      --username "$POSTGRES_USER" \
      "$RESTORE_DATABASE"

    createdb \
      --username "$POSTGRES_USER" \
      "$RESTORE_DATABASE"
  '

"${compose[@]}" exec -T \
  -e RESTORE_DATABASE="${RESTORE_DATABASE}" \
  postgres \
  sh -ec '
    export PGPASSWORD="$POSTGRES_PASSWORD"

    pg_restore \
      --username "$POSTGRES_USER" \
      --dbname "$RESTORE_DATABASE" \
      --no-owner \
      --no-acl
  ' < "${workdir}/snapshot/postgres.dump"

BACKUP_WORKDIR="${workdir}/snapshot" \
"${compose[@]}" \
  --profile ops \
  run --rm \
  -e RESTORE_BUCKET="${RESTORE_BUCKET}" \
  minio-client '
    mc alias set \
      target \
      http://minio:9000 \
      "$MINIO_ROOT_USER" \
      "$MINIO_ROOT_PASSWORD"

    mc mb \
      --ignore-existing \
      "target/$RESTORE_BUCKET"

    mc mirror \
      --overwrite \
      /backup/minio \
      "target/$RESTORE_BUCKET"
  '

echo "Restore drill completed."
echo "Database: ${RESTORE_DATABASE}"
echo "Bucket: ${RESTORE_BUCKET}"