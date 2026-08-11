#!/usr/bin/env bash
# End-to-end Compose smoke for the deployable modular-monolith baseline.
#
# It deliberately exercises public HTTP contracts rather than Django internals:
# health, authentication, dashboard/student reads, a valid comprehensive XLSX
# import, and a report preview based on the imported enrollment.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SMOKE_RUN_ID="${GITHUB_RUN_ID:-$(date +%s)-$$}"
SMOKE_SUFFIX="$(printf '%s' "$SMOKE_RUN_ID" | tr -cd '[[:alnum:]]' | tr '[:upper:]' '[:lower:]')"
SMOKE_PROJECT_NAME="${SMOKE_PROJECT_NAME:-hamamoozsmoke${SMOKE_SUFFIX}}"
SMOKE_API_PORT="${SMOKE_API_PORT:-18000}"
SMOKE_FRONTEND_PORT="${SMOKE_FRONTEND_PORT:-15173}"
SMOKE_ADMIN_USERNAME="${SMOKE_ADMIN_USERNAME:-smoke-admin}"
SMOKE_ADMIN_PASSWORD="${SMOKE_ADMIN_PASSWORD:-Smoke-${SMOKE_SUFFIX}-ChangeMe!}"
SMOKE_POSTGRES_USER="hamamooz"
SMOKE_POSTGRES_DB="hamamooz"
SMOKE_POSTGRES_PASSWORD="smoke-postgres-${SMOKE_SUFFIX}"
SMOKE_DJANGO_SECRET_KEY="smoke-${SMOKE_SUFFIX}-$(date +%s)-change-before-production"

DOCKER_BIN="${DOCKER_BIN:-docker}"
SMOKE_PYTHON="${SMOKE_PYTHON:-}"
# Keep the generated Compose env file under the workspace.  This makes it
# visible both to native Docker and to Docker Desktop invoked from WSL.
WORK_DIR="$(mktemp -d "$ROOT_DIR/.smoke-tmp.XXXXXX")"
COMPOSE_ENV_FILE="$WORK_DIR/compose.env"
{
    printf '%s\n' "HAMAMOOZ_API_PORT=${SMOKE_API_PORT}"
    printf '%s\n' "HAMAMOOZ_FRONTEND_PORT=${SMOKE_FRONTEND_PORT}"
    printf '%s\n' 'SEED_DEMO=true'
    printf '%s\n' "SEED_ADMIN_USERNAME=${SMOKE_ADMIN_USERNAME}"
    printf '%s\n' "SEED_ADMIN_PASSWORD=${SMOKE_ADMIN_PASSWORD}"
    printf '%s\n' "POSTGRES_DB=${SMOKE_POSTGRES_DB}"
    printf '%s\n' "POSTGRES_USER=${SMOKE_POSTGRES_USER}"
    printf '%s\n' "POSTGRES_PASSWORD=${SMOKE_POSTGRES_PASSWORD}"
    printf '%s\n' "DJANGO_SECRET_KEY=${SMOKE_DJANGO_SECRET_KEY}"
} > "$COMPOSE_ENV_FILE"
COMPOSE_ENV_ARGUMENT="$COMPOSE_ENV_FILE"
DOCKER_WORK_DIR_ARGUMENT="$WORK_DIR"
if [[ "$DOCKER_BIN" == *.exe ]] && command -v wslpath >/dev/null 2>&1; then
    COMPOSE_ENV_ARGUMENT="$(wslpath -w "$COMPOSE_ENV_FILE")"
    DOCKER_WORK_DIR_ARGUMENT="$(wslpath -w "$WORK_DIR")"
fi
SMOKE_UPLOAD_PATH="$WORK_DIR/integration-comprehensive.xlsx"
# Git for Windows can invoke curl.exe, which does not understand the POSIX
# /d/... path used by its shell when a multipart @file value is parsed.
if [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* ]] \
    && command -v cygpath >/dev/null 2>&1; then
    SMOKE_UPLOAD_PATH="$(cygpath -m "$SMOKE_UPLOAD_PATH")"
fi
COMPOSE=("$DOCKER_BIN" compose --env-file "$COMPOSE_ENV_ARGUMENT" -p "$SMOKE_PROJECT_NAME")
FRONTEND_URL="http://127.0.0.1:${SMOKE_FRONTEND_PORT}"
DIRECT_API_URL="http://127.0.0.1:${SMOKE_API_PORT}/api/v1"
API_URL="${FRONTEND_URL}/api/v1"
SMOKE_STUDENT_NUMBER="smoke-${SMOKE_SUFFIX}"
SMOKE_NATIONAL_ID="9000000001"

cleanup() {
    local exit_code=$?
    if [[ "${KEEP_SMOKE_CONTAINERS:-false}" != "true" ]]; then
        "${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
    fi
    rm -rf "$WORK_DIR"
    trap - EXIT
    exit "$exit_code"
}
trap cleanup EXIT

fail() {
    printf '\nIntegration smoke failed: %s\n' "$*" >&2
    "${COMPOSE[@]}" ps >&2 || true
    "${COMPOSE[@]}" logs --tail=160 release bootstrap web worker frontend db redis-cache redis-broker >&2 || true
    exit 1
}

resolve_smoke_python() {
    if [[ -n "$SMOKE_PYTHON" ]]; then
        "$SMOKE_PYTHON" -c 'import sys' >/dev/null 2>&1 \
            || fail "Configured SMOKE_PYTHON is not executable: ${SMOKE_PYTHON}"
        return
    fi
    local candidate
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 \
            && "$candidate" -c 'import sys' >/dev/null 2>&1; then
            # Preserve the resolved executable because Docker Desktop shells may
            # prepend platform-specific aliases to PATH while the stack starts.
            SMOKE_PYTHON="$(command -v "$candidate")"
            return
        fi
    done
    fail 'A working Python 3 interpreter is required for the integration fixture.'
}

wait_for_command() {
    local label="$1"
    shift
    for _ in $(seq 1 90); do
        if "$@" >/dev/null 2>&1; then
            printf 'Ready: %s\n' "$label"
            return 0
        fi
        sleep 2
    done
    fail "Timed out waiting for ${label}."
}

wait_for_http() {
    local label="$1"
    local url="$2"
    wait_for_command "$label" curl --fail --silent --show-error --max-time 5 "$url"
}

expect_http() {
    local expected_status="$1"
    local response_file="$2"
    shift 2

    local actual_status
    actual_status="$(curl --connect-timeout 5 --max-time 30 --silent --show-error --output "$response_file" --write-out '%{http_code}' "$@")" || fail "Request transport failed: $*"
    if [[ "$actual_status" != "$expected_status" ]]; then
        printf 'Unexpected HTTP status %s (expected %s). Response:\n' "$actual_status" "$expected_status" >&2
        cat "$response_file" >&2 || true
        fail "HTTP contract check failed."
    fi
}

json_value() {
    local source_file="$1"
    local dotted_path="$2"
    "$SMOKE_PYTHON" - "$source_file" "$dotted_path" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    value = json.load(source)

for key in sys.argv[2].split("."):
    value = value[key]

if value is None:
    raise SystemExit(1)
print(value)
PY
}

json_result_id_by_field() {
    local source_file="$1"
    local field="$2"
    local expected_value="$3"
    "$SMOKE_PYTHON" - "$source_file" "$field" "$expected_value" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    payload = json.load(source)

items = payload.get("results", payload) if isinstance(payload, dict) else payload
for item in items:
    if str(item.get(sys.argv[2])) == sys.argv[3]:
        print(item["id"])
        break
else:
    raise SystemExit(1)
PY
}

resolve_smoke_python
printf 'Building Compose images for project %s\n' "$SMOKE_PROJECT_NAME"
"${COMPOSE[@]}" config --quiet
"${COMPOSE[@]}" build
"${COMPOSE[@]}" up -d

wait_for_command "PostgreSQL" "${COMPOSE[@]}" exec -T db pg_isready -U "$SMOKE_POSTGRES_USER" -d "$SMOKE_POSTGRES_DB"
wait_for_command "Redis cache" "${COMPOSE[@]}" exec -T redis-cache redis-cli ping
wait_for_command "Redis broker" "${COMPOSE[@]}" exec -T redis-broker redis-cli ping
wait_for_http "Django live health" "${DIRECT_API_URL}/health/live/"
wait_for_http "Django ready health" "${DIRECT_API_URL}/health/ready/"
wait_for_http "Frontend health" "${FRONTEND_URL}/healthz"
wait_for_http "Frontend API proxy readiness" "${API_URL}/health/ready/"

"$SMOKE_PYTHON" - "$WORK_DIR/login.json" "$SMOKE_ADMIN_USERNAME" "$SMOKE_ADMIN_PASSWORD" <<'PY'
import json
import sys

with open(sys.argv[1], "w", encoding="utf-8") as target:
    json.dump({"username": sys.argv[2], "password": sys.argv[3]}, target)
PY

expect_http 200 "$WORK_DIR/token.json" \
    -X POST "$API_URL/auth/token/" \
    -H 'Content-Type: application/json' \
    --data-binary "@$WORK_DIR/login.json"
ACCESS_TOKEN="$(json_value "$WORK_DIR/token.json" access)"
REFRESH_TOKEN="$(json_value "$WORK_DIR/token.json" refresh)"
AUTH_HEADERS=(-H "Authorization: Bearer ${ACCESS_TOKEN}")

expect_http 200 "$WORK_DIR/dashboard.json" \
    "$API_URL/dashboard/summary/" "${AUTH_HEADERS[@]}"
expect_http 200 "$WORK_DIR/students-before-import.json" \
    "$API_URL/students/?page_size=10" "${AUTH_HEADERS[@]}"
expect_http 200 "$WORK_DIR/schools.json" \
    "$API_URL/schools/?page_size=100" "${AUTH_HEADERS[@]}"
SCHOOL_ID="$(json_result_id_by_field "$WORK_DIR/schools.json" code branch-01)" \
    || fail 'The demo seed did not expose school branch-01.'
SCOPE_HEADERS=("${AUTH_HEADERS[@]}" -H "X-School-ID: ${SCHOOL_ID}")

# The deployed backend image contains openpyxl and the official template.  Seed
# one valid row from the demo scope so the request validates the complete async
# import workflow instead of merely accepting a file extension.
"${COMPOSE[@]}" exec -T \
    -e "SMOKE_STUDENT_NUMBER=${SMOKE_STUDENT_NUMBER}" \
    -e "SMOKE_NATIONAL_ID=${SMOKE_NATIONAL_ID}" \
    web python - <<'PY'
import os

from openpyxl import load_workbook

workbook = load_workbook('/app/docs/import_templates/comprehensive_school_template.xlsx')
classes = workbook['کلاس‌بندی']
students = workbook['دانش‌آموزان']

for column, value in enumerate([1, 'branch-01', '1405-1406', '7-a', 'هفتم الف', 'grade-7', 35], start=1):
    classes.cell(row=5, column=column, value=value)
for column, value in enumerate(
    [1, '1', os.environ['SMOKE_NATIONAL_ID'], os.environ['SMOKE_STUDENT_NUMBER'], 'آزمون', 'دود', 'پسر', '2012-01-01', '7-a'],
    start=1,
):
    students.cell(row=5, column=column, value=value)

workbook.save('/tmp/integration-comprehensive.xlsx')
PY
WEB_CONTAINER="$("${COMPOSE[@]}" ps -q web)"
[[ -n "$WEB_CONTAINER" ]] || fail 'Could not resolve the web container for the XLSX fixture.'
"$DOCKER_BIN" cp \
    "${WEB_CONTAINER}:/tmp/integration-comprehensive.xlsx" \
    "$DOCKER_WORK_DIR_ARGUMENT/integration-comprehensive.xlsx"

expect_http 201 "$WORK_DIR/import-created.json" \
    -X POST "$API_URL/imports/" "${SCOPE_HEADERS[@]}" \
    -F "school=${SCHOOL_ID}" \
    -F 'import_type=comprehensive_school' \
    -F "source_file=@${SMOKE_UPLOAD_PATH};type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
IMPORT_ID="$(json_value "$WORK_DIR/import-created.json" id)"

IMPORT_COMPLETED=false
for _ in $(seq 1 90); do
    expect_http 200 "$WORK_DIR/import-status.json" \
        "$API_URL/imports/${IMPORT_ID}/" "${SCOPE_HEADERS[@]}"
    IMPORT_STATUS="$(json_value "$WORK_DIR/import-status.json" status)"
    case "$IMPORT_STATUS" in
        completed)
            IMPORT_COMPLETED=true
            break
            ;;
        failed|cancelled)
            cat "$WORK_DIR/import-status.json" >&2
            fail "The comprehensive XLSX import ended as ${IMPORT_STATUS}."
            ;;
    esac
    sleep 2
done
[[ "$IMPORT_COMPLETED" == true ]] || fail 'The comprehensive XLSX import did not complete in time.'

expect_http 200 "$WORK_DIR/enrollments.json" \
    -G "$API_URL/enrollments/" "${SCOPE_HEADERS[@]}" \
    --data-urlencode "search=${SMOKE_STUDENT_NUMBER}" \
    --data-urlencode 'page_size=10'
ENROLLMENT_ID="$(json_result_id_by_field "$WORK_DIR/enrollments.json" student_number "$SMOKE_STUDENT_NUMBER")" \
    || fail 'The imported enrollment was not returned by the scoped API.'

expect_http 200 "$WORK_DIR/terms.json" \
    "$API_URL/terms/?page_size=100" "${AUTH_HEADERS[@]}"
TERM_ID="$(json_result_id_by_field "$WORK_DIR/terms.json" code first)" \
    || fail 'The demo seed did not expose the first academic term.'
"$SMOKE_PYTHON" - "$WORK_DIR/report-preview.json" "$TERM_ID" "$ENROLLMENT_ID" <<'PY'
import json
import sys

with open(sys.argv[1], 'w', encoding='utf-8') as target:
    json.dump(
        {
            'report_type': 'student_report_card',
            'term': sys.argv[2],
            'enrollment': sys.argv[3],
        },
        target,
    )
PY
expect_http 200 "$WORK_DIR/report-preview-response.json" \
    -X POST "$API_URL/reports/preview/" "${SCOPE_HEADERS[@]}" \
    -H 'Content-Type: application/json' \
    --data-binary "@$WORK_DIR/report-preview.json"
"$SMOKE_PYTHON" - "$WORK_DIR/report-preview-response.json" "$SMOKE_STUDENT_NUMBER" <<'PY'
import json
import sys

with open(sys.argv[1], encoding='utf-8') as source:
    payload = json.load(source)

reports = payload.get('snapshot', {}).get('reports', [])
if len(reports) != 1 or reports[0].get('student', {}).get('student_number') != sys.argv[2]:
    raise SystemExit('Report preview did not contain the imported student.')
if not payload.get('html'):
    raise SystemExit('Report preview did not include rendered HTML.')
PY

"$SMOKE_PYTHON" - "$WORK_DIR/logout.json" "$REFRESH_TOKEN" <<'PY'
import json
import sys

with open(sys.argv[1], 'w', encoding='utf-8') as target:
    json.dump({'refresh': sys.argv[2]}, target)
PY
expect_http 204 "$WORK_DIR/logout-response.txt" \
    -X POST "$API_URL/auth/logout/" "${AUTH_HEADERS[@]}" \
    -H 'Content-Type: application/json' \
    --data-binary "@$WORK_DIR/logout.json"

printf 'Compose integration smoke passed for project %s.\n' "$SMOKE_PROJECT_NAME"
