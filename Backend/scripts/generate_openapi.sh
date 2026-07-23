#!/bin/sh
set -eu
OUTPUT=${1:-build/openapi.yaml}
mkdir -p "$(dirname "$OUTPUT")"
python manage.py spectacular --api-version v1 --file "$OUTPUT" --validate
printf 'OpenAPI schema generated: %s\n' "$OUTPUT"
