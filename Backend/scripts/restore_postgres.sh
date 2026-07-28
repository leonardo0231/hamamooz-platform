#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /path/to/backup.dump" >&2
  exit 2
fi

backup="$1"
test -f "$backup"
backup_dir="$(dirname "$backup")"
backup_name="$(basename "$backup")"
test -f "$backup.sha256" && (
  cd "$backup_dir"
  sha256sum -c "$backup_name.sha256"
)

pg_restore --clean --if-exists --no-owner --no-acl --dbname="$PGDATABASE" "$backup"
