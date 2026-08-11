from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from hamamooz.apps.academics.models import CourseOffering, SubjectResult
from hamamooz.apps.accounts.models import Role, RoleAssignment, User
from hamamooz.apps.analytics.models import AnalyticsRun, StudentRiskSignal
from hamamooz.apps.counseling.models import CounselingCase
from hamamooz.apps.organizations.models import Term
from hamamooz.apps.recommendations.models import Recommendation


@pytest.mark.django_db
def test_risk_signal_catalog_is_school_scoped(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        "/api/v1/analytics/risk-signals/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    assert response.data["count"] == 0


@pytest.mark.django_db
def test_academic_drop_rule_is_deterministic_and_explains_exact_evidence(api_client, base_data):
    SubjectResult.objects.create(
        enrollment=base_data["enrollments"][0],
        course_offering=base_data["offering1"],
        average=Decimal("17.40"),
        passed=True,
        formula_version="test-v1",
    )
    second_term = Term.objects.create(
        academic_year=base_data["year"],
        code=Term.Code.SECOND,
        title="Second",
        starts_on=date(2027, 1, 21),
        ends_on=date(2027, 6, 22),
        order=2,
    )
    current_offering = CourseOffering.objects.create(
        class_section=base_data["class1"],
        grade_subject=base_data["grade_subject"],
        term=second_term,
        teacher=base_data["teacher1"],
    )
    SubjectResult.objects.create(
        enrollment=base_data["enrollments"][0],
        course_offering=current_offering,
        average=Decimal("14.20"),
        passed=True,
        formula_version="test-v1",
    )
    api_client.force_authenticate(base_data["manager"])
    response = api_client.post(
        "/api/v1/analytics/runs/",
        {"enrollment": str(base_data["enrollments"][0].id)},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 201
    signal = StudentRiskSignal.objects.get(rule_code="academic_drop", state="active")
    assert signal.rule_version == 1
    assert signal.severity == "medium"
    assert signal.evidence == {
        "subject": "math",
        "previous_average": 17.4,
        "current_average": 14.2,
        "drop": 3.2,
    }
    assert signal.window == {"comparison": "previous_subject_result", "terms": 2}
    assert "3.20" in signal.explanation


@pytest.mark.django_db
def test_recommendation_catalog_starts_empty_in_school_scope(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])
    response = api_client.get(
        "/api/v1/recommendations/", HTTP_X_SCHOOL_ID=str(base_data["school1"].id)
    )
    assert response.status_code == 200
    assert response.data["count"] == 0


@pytest.mark.django_db
def test_recommendation_requires_human_review_before_approval(api_client, base_data):
    enrollment = base_data["enrollments"][0]
    run = AnalyticsRun.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=enrollment,
        status=AnalyticsRun.Status.COMPLETED,
    )
    signal = StudentRiskSignal.objects.create(
        run=run,
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=enrollment,
        rule_code="academic_drop",
        rule_version=1,
        severity="high",
        evidence={"drop": 4.0},
        explanation="Deterministic evidence",
        window={"terms": 2},
    )
    api_client.force_authenticate(base_data["manager"])
    generated = api_client.post(
        "/api/v1/recommendations/generate/",
        {"signal": str(signal.id)},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert generated.status_code == 201
    recommendation = Recommendation.objects.get(audience="guide_teacher")
    assert recommendation.status == "draft"
    assert "Deterministic" in recommendation.reason_snapshot["limitations"]

    pending = api_client.post(
        f"/api/v1/recommendations/{recommendation.id}/transition/",
        {"target_status": "pending_review"},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert pending.status_code == 200
    approval = api_client.post(
        f"/api/v1/recommendations/{recommendation.id}/transition/",
        {"target_status": "approved", "approved_text": "Schedule a supportive follow-up."},
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert approval.status_code == 200
    recommendation.refresh_from_db()
    assert recommendation.status == "approved"
    assert recommendation.approved_text == "Schedule a supportive follow-up."
    assert recommendation.decisions.count() == 2


@pytest.mark.django_db
def test_counselor_audience_recommendations_are_not_a_generic_staff_or_360_feed(
    api_client, base_data
):
    """A sibling recommendation for a counselor is private to that case owner."""

    counselor = User.objects.create_user(
        username="recommendation-counselor",
        email="recommendation-counselor@example.com",
        password="Strong-pass-123",
    )
    RoleAssignment.objects.create(
        user=counselor,
        organization=base_data["organization"],
        school=base_data["school1"],
        role=Role.COUNSELOR,
    )
    enrollment = base_data["enrollments"][0]
    CounselingCase.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=enrollment,
        assigned_counselor=counselor,
        opened_by=counselor,
        status=CounselingCase.Status.ACTIVE,
    )
    run = AnalyticsRun.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=enrollment,
        status=AnalyticsRun.Status.COMPLETED,
        completed_at=timezone.now(),
    )
    signal = StudentRiskSignal.objects.create(
        run=run,
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=enrollment,
        rule_code="discipline_repeat",
        rule_version=1,
        severity=StudentRiskSignal.Severity.HIGH,
        evidence={"events": 3},
        explanation="Private counseling follow-up is needed.",
        window={"days": 30},
    )
    recommendation = Recommendation.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=enrollment,
        source_signal=signal,
        audience=Recommendation.Audience.COUNSELOR,
        rule_code="discipline_repeat_support",
        rule_version=1,
        priority=Recommendation.Priority.HIGH,
        reason_snapshot={"private": True},
        generated_text="Private counselor-only guidance.",
    )
    headers = {"HTTP_X_SCHOOL_ID": str(base_data["school1"].id)}

    api_client.force_authenticate(base_data["manager"])
    assert api_client.get("/api/v1/recommendations/", **headers).data["count"] == 0
    assert (
        api_client.get(f"/api/v1/recommendations/{recommendation.id}/", **headers).status_code
        == 404
    )
    summary = api_client.get(
        f"/api/v1/students/{enrollment.student_id}/360/recommendations/", **headers
    )
    assert summary.status_code == 200
    assert summary.data["recommendations"] == []

    system_admin = User.objects.create_superuser(
        username="recommendation-system-admin",
        email="recommendation-system-admin@example.com",
        password="Strong-pass-123",
    )
    api_client.force_authenticate(system_admin)
    assert api_client.get("/api/v1/recommendations/", **headers).data["count"] == 0

    api_client.force_authenticate(counselor)
    visible = api_client.get("/api/v1/recommendations/", **headers)
    assert visible.status_code == 200
    assert [item["id"] for item in visible.data["results"]] == [str(recommendation.id)]
    transitioned = api_client.post(
        f"/api/v1/recommendations/{recommendation.id}/transition/",
        {"target_status": Recommendation.Status.PENDING_REVIEW},
        format="json",
        **headers,
    )
    assert transitioned.status_code == 200, transitioned.data


@pytest.mark.django_db
def test_student_affairs_can_read_risk_and_non_confidential_recommendation_scope(
    api_client, base_data
):
    deputy = User.objects.create_user(
        username="student-affairs-analytics",
        email="student-affairs-analytics@example.com",
        password="Strong-pass-123",
    )
    RoleAssignment.objects.create(
        user=deputy,
        organization=base_data["organization"],
        school=base_data["school1"],
        role=Role.STUDENT_AFFAIRS_DEPUTY,
    )
    enrollment = base_data["enrollments"][0]
    run = AnalyticsRun.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=enrollment,
        status=AnalyticsRun.Status.COMPLETED,
    )
    signal = StudentRiskSignal.objects.create(
        run=run,
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=enrollment,
        rule_code="attendance_risk",
        rule_version=1,
        severity=StudentRiskSignal.Severity.MEDIUM,
        evidence={"unexcused": 4},
        explanation="Deterministic attendance evidence.",
        window={"days": 30},
    )
    Recommendation.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=enrollment,
        source_signal=signal,
        audience=Recommendation.Audience.EDUCATIONAL_DEPUTY,
        rule_code="attendance_support",
        rule_version=1,
        priority=Recommendation.Priority.MEDIUM,
        reason_snapshot={"rule": "attendance_risk"},
        generated_text="Coordinate a supportive attendance follow-up.",
    )
    api_client.force_authenticate(deputy)
    headers = {"HTTP_X_SCHOOL_ID": str(base_data["school1"].id)}
    assert api_client.get("/api/v1/analytics/risk-signals/", **headers).data["count"] == 1
    assert api_client.get("/api/v1/recommendations/", **headers).data["count"] == 1
