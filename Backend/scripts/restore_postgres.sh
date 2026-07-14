#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /path/to/backup.dump" >&2
  exit 2
fi

backup="$1"
test -f "$backup"
test -f "$backup.sha256" && sha256sum -c "$backup.sha256"

pg_restore --clean --if-exists --no-owner --no-acl --dbname="$PGDATABASE" "$backup"
