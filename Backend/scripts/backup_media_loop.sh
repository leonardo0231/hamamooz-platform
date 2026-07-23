#!/bin/sh
set -eu

: "${BACKUP_INTERVAL_SECONDS:=86400}"
: "${BACKUP_RETENTION_DAYS:=14}"
: "${MEDIA_SOURCE_DIR:=/media}"
: "${BACKUP_DIR:=/backups/media}"

mkdir -p "$BACKUP_DIR"
while true; do
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  archive="$BACKUP_DIR/hamamooz_media_${timestamp}.tar.gz"
  tar -C "$MEDIA_SOURCE_DIR" -czf "$archive" .
  (
    cd "$BACKUP_DIR"
    sha256sum "$(basename "$archive")" > "$(basename "$archive").sha256"
  )
  find "$BACKUP_DIR" -type f -name 'hamamooz_media_*.tar.gz*' \
    -mtime "+$BACKUP_RETENTION_DAYS" -delete
  sleep "$BACKUP_INTERVAL_SECONDS"
done
