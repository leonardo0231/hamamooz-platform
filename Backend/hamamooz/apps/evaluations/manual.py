from django.db import transaction

from .catalog import FRAMEWORK_VERSION
from .models import MetricScore, MonthlyEvaluation


@transaction.atomic
def upsert_manual_evaluation(*, enrollment, month_no, note, metrics, actor):
    """Create or update one monthly evaluation without bypassing domain identity.

    Manual entry is intentionally an upsert for one enrollment/month/framework. Metrics not
    present in the request are preserved so a staff member can save a partial evaluation and
    continue later without accidentally erasing previously recorded values. If the evaluation
    originally came from an import, its source_import_job is preserved as provenance while the
    audit event records the later manual edit.
    """

    evaluation = (
        MonthlyEvaluation.all_objects.select_for_update()
        .filter(
            enrollment=enrollment,
            month_no=month_no,
            framework_version=FRAMEWORK_VERSION,
        )
        .first()
    )
    created = evaluation is None
    restored = False
    if evaluation is None:
        evaluation = MonthlyEvaluation(
            enrollment=enrollment,
            month_no=month_no,
            framework_version=FRAMEWORK_VERSION,
            recorded_by=actor,
        )
    elif evaluation.is_deleted:
        evaluation.is_deleted = False
        evaluation.deleted_at = None
        restored = True

    evaluation.note = note
    evaluation.recorded_by = actor
    evaluation.full_clean(exclude=["id"])
    evaluation.save()

    created_metrics = 0
    updated_metrics = 0
    unchanged_metrics = 0
    existing = {
        score.metric_code: score
        for score in MetricScore.objects.select_for_update().filter(evaluation=evaluation)
    }
    for entry in metrics:
        metric_code = entry["metric_code"]
        value = entry["value"]
        score = existing.get(metric_code)
        if score is None:
            MetricScore.objects.create(
                evaluation=evaluation,
                metric_code=metric_code,
                value=value,
            )
            created_metrics += 1
        elif score.value == value:
            unchanged_metrics += 1
        else:
            score.value = value
            score.full_clean(exclude=["id"])
            score.save(update_fields=["value", "updated_at"])
            updated_metrics += 1

    return evaluation, {
        "created": created,
        "restored": restored,
        "metrics_created": created_metrics,
        "metrics_updated": updated_metrics,
        "metrics_unchanged": unchanged_metrics,
    }


@transaction.atomic
def delete_manual_evaluation(*, evaluation):
    """Soft-delete a manual monthly evaluation while preserving its metric history."""

    locked = MonthlyEvaluation.objects.select_for_update().get(pk=evaluation.pk)
    locked.delete()
    return locked
