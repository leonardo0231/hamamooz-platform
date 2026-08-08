#!/bin/sh
set -eu

: "${BACKUP_DIR:=./backups}"
: "${BACKUP_RETENTION_DAYS:=14}"

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="$BACKUP_DIR/hamamooz_${timestamp}.dump"
target_name="$(basename "$target")"

pg_dump --format=custom --no-owner --no-acl --file="$target"
(cd "$BACKUP_DIR" && sha256sum "$target_name" > "$target_name.sha256")
find "$BACKUP_DIR" -type f -name 'hamamooz_*.dump*' -mtime "+$BACKUP_RETENTION_DAYS" -delete
printf '%s\n' "$target"
