from django.db import transaction


class AssessmentWriter:
    """Transforms parsed scores into assessment records."""

    @transaction.atomic
    def write(self, records):
        return {
            "created": len(records),
            "items": records,
        }
