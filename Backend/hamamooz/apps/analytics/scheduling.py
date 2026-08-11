from django.db import transaction


def schedule_targeted_analytics(enrollment_ids):
    """Queue recomputation only after the source transaction is durable."""
    normalized_ids = tuple(sorted({str(value) for value in enrollment_ids if value}))
    if not normalized_ids:
        return

    def dispatch():
        from .tasks import run_targeted_analytics

        for enrollment_id in normalized_ids:
            run_targeted_analytics.delay(enrollment_id)

    transaction.on_commit(dispatch)
