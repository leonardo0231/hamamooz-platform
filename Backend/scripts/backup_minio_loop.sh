#!/bin/sh
set -eu

: "${BACKUP_INTERVAL_SECONDS:=86400}"
: "${BACKUP_RETENTION_DAYS:=14}"
: "${AWS_STORAGE_BUCKET_NAME:?AWS_STORAGE_BUCKET_NAME must be set}"

mc alias set local "${AWS_S3_ENDPOINT_URL:-http://minio:9000}" \
  "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID must be set}" \
  "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY must be set}"

while true; do
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  target="/backups/minio/${timestamp}"
  mkdir -p "$target"
  mc mirror --overwrite "local/${AWS_STORAGE_BUCKET_NAME}" "$target"
  find /backups/minio -mindepth 1 -maxdepth 1 -type d \
    -mtime "+$BACKUP_RETENTION_DAYS" -exec rm -rf {} +
  sleep "$BACKUP_INTERVAL_SECONDS"
done
