# Direct `Data/` import and monthly report cards

The application can now read the repository's mounted `Data/` directory on the
server. A browser upload is not required.

## Source contract

```text
Data/
├── Excel/   *.xlsx, *.xls, and *.xlsm workbooks (all nested folders are scanned)
└── Photo/   *.jpg, *.jpeg, *.png, *.webp, and supported *.zip archives
```

Photo filenames are matched by national code. A leading zero may be restored
when the source filename contains fewer than ten digits. Duplicate portraits
are reported for review; an existing stored portrait is preserved unless
`overwrite_photos` is explicitly enabled.

Every workbook receives its own `ImportJob` for provenance. The parent
`DataPathImport` stores the manifest, warnings, unsupported files, photo
reconciliation result, and report batches created by the run.

## API

With the server-side `Data/` directory mounted at the configured
`HAMAMOOZ_DATA_ROOT`, an authorized manager starts a run with:

```http
POST /api/v1/imports/from-data-path/
Content-Type: application/json

{
  "school": "<school-uuid>",
  "generate_reports": true,
  "report_month": 4,
  "overwrite_photos": false
}
```

The response is `202 Accepted`. Poll
`GET /api/v1/imports/data-path-imports/` for status and the complete result.
The mounted path itself is not accepted from the client; the API only uses the
configured server path.

## CLI

For an operator-run import or a read-only manifest scan:

```bash
python manage.py import_data_path \
  --organization-id <organization-uuid> \
  --school-id <school-uuid> \
  --requested-by <user-uuid> \
  --month 4

python manage.py import_data_path \
  --organization-id ignored \
  --school-id ignored \
  --requested-by ignored \
  --dry-run
```

The import preserves both a typed value and the source cell text. This is
needed because the operational workbooks contain legacy 0–5 rubrics, 0–20
scores, signed progress values, decimal values, and explicit text such as
`ندارد`. Only values with a known unit are included in the analytical average;
unknown, signed-delta, and not-recorded values remain visible in the report.

## Monthly report cards

Data imports create `data_monthly` report batches with no official `Term`
dependency. The selected month is either `report_month` or the latest month
found in the imported assessment records. Each batch produces one PDF report
card per active enrollment and a downloadable ZIP through:

```http
GET /api/v1/reports/batches/<batch-uuid>/download/
```

The frontend exposes both the direct Data scan in Imports and the monthly
report/ZIP flow in Reports. Official term reports remain available separately
and continue to require locked course assessments.

## Container mount

The root and backend Compose files mount the repository directory read-only:

```yaml
- ./Data:/app/Data:ro
HAMAMOOZ_DATA_ROOT: /app/Data
```

This keeps source workbooks and portraits immutable to the application while
allowing the resulting student photos, import records, report archives, and
ZIP files to be stored in the normal database/media locations.
