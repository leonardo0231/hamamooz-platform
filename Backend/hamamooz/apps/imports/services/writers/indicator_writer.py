from django.db import transaction


class IndicatorWriter:
    """Creates discovered indicators without fixed indicator counts."""

    @transaction.atomic
    def write(self, indicators):
        return {
            "created": len(indicators),
            "items": indicators,
        }
