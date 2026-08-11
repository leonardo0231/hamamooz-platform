from django.db import transaction
from django.utils import timezone

from hamamooz.apps.students.models import Enrollment

from .models import AnalyticsRuleConfig, AnalyticsRun, OperationalAlert, StudentRiskSignal
from .rules import RULES


def effective_rules_for(organization):
    configured = {
        (config.rule_code, config.rule_version): config
        for config in AnalyticsRuleConfig.objects.filter(organization=organization)
    }
    for rule in RULES:
        config = configured.get((rule.code, rule.version))
        if config and not config.enabled:
            continue
        parameters = {**rule.default_parameters, **(config.parameters if config else {})}
        yield rule, parameters


def run_for_enrollment(*, enrollment_id, trigger=AnalyticsRun.Trigger.MANUAL, requested_by=None):
    """Run code-versioned rules under one enrollment lock and snapshot outputs.

    Each completed run keeps immutable signal evidence.  Older active signals are
    explicitly superseded, avoiding a mutable opaque ``risk = 82`` record.
    """
    with transaction.atomic():
        enrollment = (
            Enrollment.objects.select_for_update()
            .select_related("school__organization")
            .get(pk=enrollment_id)
        )
        organization = enrollment.school.organization
        run = AnalyticsRun.objects.create(
            organization=organization,
            school=enrollment.school,
            enrollment=enrollment,
            trigger=trigger,
            requested_by=requested_by,
            status=AnalyticsRun.Status.RUNNING,
            started_at=timezone.now(),
        )
        rules = list(effective_rules_for(organization))
        run.rule_snapshot = [
            {"rule_code": rule.code, "rule_version": rule.version, "parameters": parameters}
            for rule, parameters in rules
        ]
        run.save(update_fields=["rule_snapshot", "updated_at"])
        StudentRiskSignal.objects.filter(
            enrollment=enrollment, state=StudentRiskSignal.State.ACTIVE
        ).update(state=StudentRiskSignal.State.SUPERSEDED)
        for rule, parameters in rules:
            for candidate in rule.evaluate(enrollment, parameters):
                signal = StudentRiskSignal.objects.create(
                    run=run,
                    organization=organization,
                    school=enrollment.school,
                    enrollment=enrollment,
                    rule_code=rule.code,
                    rule_version=rule.version,
                    severity=candidate.severity,
                    evidence=candidate.evidence,
                    explanation=candidate.explanation,
                    window=candidate.window,
                )
                if signal.severity in {
                    StudentRiskSignal.Severity.HIGH,
                    StudentRiskSignal.Severity.CRITICAL,
                }:
                    OperationalAlert.objects.create(signal=signal)
        run.status = AnalyticsRun.Status.COMPLETED
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "completed_at", "updated_at"])
        return run
