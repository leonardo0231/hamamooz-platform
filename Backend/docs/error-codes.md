# Error Codes

## Infrastructure/API baseline

- `authentication_required`
- `permission_denied`
- `validation_error`
- `not_found`
- `api_error`

## Reserved MVP domain codes

- `school_access_denied`
- `duplicate_national_id`
- `enrollment_already_exists`
- `invalid_score_range`
- `invalid_score_transition`
- `score_is_locked`
- `import_validation_failed`
- `report_generation_failed`

Domain services will raise typed exceptions that map consistently to this catalog.
