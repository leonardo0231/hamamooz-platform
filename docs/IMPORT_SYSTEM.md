# Import System Architecture

## Flow

Operator → Upload → Analyze → Preview → Confirm → Import → Report Generation

## Import States

- UPLOADED
- ANALYZING
- PREVIEW_READY
- CONFIRMED
- PROCESSING
- COMPLETED
- FAILED
- CANCELLED

## Components

- Workbook analyzer
- Dynamic parser
- Column mapping
- Validation
- Import executor
- Student/enrollment/assessment writers
- Photo ZIP importer

## Reporting

Reports are generated from frozen snapshots. The rendering pipeline supports HTML/CSS based layouts and PDF generation.

## Verification Commands

```bash
pytest
python manage.py test
```

## Troubleshooting

Check ImportJob errors, validation warnings, and failed batch report items before retrying.
