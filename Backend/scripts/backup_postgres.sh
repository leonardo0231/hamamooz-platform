#!/bin/sh
set -eu

: "${BACKUP_DIR:=./backups}"
: "${BACKUP_RETENTION_DAYS:=14}"

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="$BACKUP_DIR/hamamooz_${timestamp}.dump"

pg_dump --format=custom --no-owner --no-acl --file="$target"
sha256sum "$target" > "$target.sha256"
find "$BACKUP_DIR" -type f -name 'hamamooz_*.dump*' -mtime "+$BACKUP_RETENTION_DAYS" -delete
printf '%s\n' "$target"
