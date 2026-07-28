#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /path/to/hamamooz_media_TIMESTAMP.tar.gz" >&2
  exit 2
fi

archive="$1"
: "${MEDIA_TARGET_DIR:=/media}"
test -f "$archive"
archive_dir="$(dirname "$archive")"
archive_name="$(basename "$archive")"
if [ -f "$archive.sha256" ]; then
  (
    cd "$archive_dir"
    sha256sum -c "$archive_name.sha256"
  )
fi
mkdir -p "$MEDIA_TARGET_DIR"
tar -C "$MEDIA_TARGET_DIR" -xzf "$archive"
