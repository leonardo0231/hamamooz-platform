from django.db import transaction


class EnrollmentWriter:
    """Maps imported class information to enrollment records."""

    def __init__(self, school):
        self.school = school

    @transaction.atomic
    def write(self, rows):
        return {
            "created": len(rows),
            "items": rows,
        }
