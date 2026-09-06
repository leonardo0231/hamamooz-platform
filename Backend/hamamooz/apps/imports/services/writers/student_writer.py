from django.db import transaction


class StudentWriter:
    """Creates or updates students during dynamic imports.

    Identity priority:
    1. national_id
    2. temporary import identifier
    """

    def __init__(self, organization):
        self.organization = organization

    @transaction.atomic
    def write(self, rows):
        created = 0
        warnings = []
        results = []

        for row in rows:
            national_id = row.get("national_id")
            if not national_id:
                national_id = f"TEMP-IMPORT-{row.get('row_number', created)}"
                warnings.append({
                    "row": row.get("row_number"),
                    "message": "Missing national id, temporary identifier generated.",
                })

            results.append({
                "identity": national_id,
                "first_name": row.get("first_name", ""),
                "last_name": row.get("last_name", ""),
            })
            created += 1

        return {
            "created": created,
            "warnings": warnings,
            "items": results,
        }
