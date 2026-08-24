from datetime import timedelta

import pytest
from django.utils import timezone

from hamamooz.apps.accounts.models import Role, RoleAssignment, User
from hamamooz.apps.recommendations.models import Recommendation
from hamamooz.apps.reports.models import ReportArchive
from hamamooz.apps.students.models import Guardian, GuardianAccount, StudentAccount, StudentGuardian
from hamamooz.apps.summers.models import SummerProgram, SummerRegistration


@pytest.mark.django_db
def test_non_portal_user_cannot_read_portal_children(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])
    response = api_client.get("/api/v1/portal/me/children/")
    assert response.status_code == 403


def guardian_portal_user(base_data):
    user = User.objects.create_user(
        username="portal-parent", email="portal-parent@example.com", password="Strong-pass-123"
    )
    guardian = Guardian.objects.create(
        organization=base_data["organization"],
        first_name="Portal",
        last_name="Parent",
        phone_primary="09120000000",
    )
    GuardianAccount.objects.create(user=user, guardian=guardian, verified_at=timezone.now())
    StudentGuardian.objects.create(
        student=base_data["students"][0],
        guardian=guardian,
        relationship=StudentGuardian.Relationship.MOTHER,
        is_primary=True,
    )
    return user


@pytest.mark.django_db
def test_guardian_portal_derives_children_from_relationship_and_blocks_idor(api_client, base_data):
    parent = guardian_portal_user(base_data)
    api_client.force_authenticate(parent)

    children = api_client.get("/api/v1/portal/me/children/")
    assert children.status_code == 200
    assert [child["id"] for child in children.data["children"]] == [
        str(base_data["students"][0].id)
    ]

    idor = api_client.get(f"/api/v1/portal/children/{base_data['students'][1].id}/reports/")
    assert idor.status_code == 404


@pytest.mark.django_db
def test_parent_portal_exposes_only_released_reports_and_approved_parent_recommendations(
    api_client, base_data
):
    parent = guardian_portal_user(base_data)
    enrollment = base_data["enrollments"][0]
    released = ReportArchive.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        term=base_data["term"],
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        status=ReportArchive.Status.COMPLETED,
        enrollment=enrollment,
        requested_by=base_data["manager"],
        released_by=base_data["manager"],
        released_at=timezone.now(),
    )
    ReportArchive.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        term=base_data["term"],
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        status=ReportArchive.Status.COMPLETED,
        enrollment=enrollment,
        requested_by=base_data["manager"],
    )
    Recommendation.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=enrollment,
        audience=Recommendation.Audience.PARENT,
        rule_code="support",
        rule_version=1,
        priority=Recommendation.Priority.MEDIUM,
        reason_snapshot={"evidence": "safe"},
        generated_text="Draft",
        approved_text="Approved parent guidance",
        status=Recommendation.Status.APPROVED,
        reviewer=base_data["manager"],
        approved_at=timezone.now(),
    )
    Recommendation.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=enrollment,
        audience=Recommendation.Audience.PARENT,
        rule_code="hidden",
        rule_version=1,
        priority=Recommendation.Priority.MEDIUM,
        reason_snapshot={},
        generated_text="Draft",
        status=Recommendation.Status.PENDING_REVIEW,
    )
    api_client.force_authenticate(parent)
    reports = api_client.get(f"/api/v1/portal/children/{enrollment.student_id}/reports/")
    recommendations = api_client.get(
        f"/api/v1/portal/children/{enrollment.student_id}/recommendations/"
    )

    assert reports.status_code == 200
    assert [item["id"] for item in reports.data["reports"]] == [str(released.id)]
    assert recommendations.status_code == 200
    assert recommendations.data["recommendations"] == [
        {
            "id": str(Recommendation.objects.get(rule_code="support").id),
            "priority": "medium",
            "approved_text": "Approved parent guidance",
            "approved_at": recommendations.data["recommendations"][0]["approved_at"],
        }
    ]


@pytest.mark.django_db
def test_parent_portal_exposes_released_summer_report_without_an_ordinary_term(
    api_client, base_data
):
    parent = guardian_portal_user(base_data)
    enrollment = base_data["enrollments"][0]
    program = SummerProgram.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        title="تابستان دانش‌آموز",
    )
    registration = SummerRegistration.objects.create(program=program, enrollment=enrollment)
    archive = ReportArchive.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        term=None,
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        layout_key="summer_report",
        status=ReportArchive.Status.COMPLETED,
        summer_program=program,
        summer_registration=registration,
        requested_by=base_data["manager"],
        released_by=base_data["manager"],
        released_at=timezone.now(),
    )

    api_client.force_authenticate(parent)
    response = api_client.get(f"/api/v1/portal/children/{enrollment.student_id}/reports/")

    assert response.status_code == 200
    assert response.data["reports"] == [
        {
            "id": str(archive.id),
            "report_type": ReportArchive.ReportType.STUDENT_REPORT_CARD,
            "output_format": ReportArchive.OutputFormat.PDF,
            "term": "تابستان دانش‌آموز",
            "created_at": response.data["reports"][0]["created_at"],
            "released_at": response.data["reports"][0]["released_at"],
        }
    ]


@pytest.mark.django_db
def test_parent_portal_never_returns_an_expired_approved_recommendation(
    api_client, base_data
):
    parent = guardian_portal_user(base_data)
    enrollment = base_data["enrollments"][0]
    Recommendation.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=enrollment,
        audience=Recommendation.Audience.PARENT,
        rule_code="expired-family-guidance",
        rule_version=1,
        priority=Recommendation.Priority.MEDIUM,
        generated_text="پیشنهاد اولیه",
        approved_text="پیشنهاد تأییدشده منقضی",
        status=Recommendation.Status.APPROVED,
        reviewer=base_data["manager"],
        approved_at=timezone.now() - timedelta(days=2),
        expires_at=timezone.now() - timedelta(days=1),
    )

    api_client.force_authenticate(parent)
    response = api_client.get(
        f"/api/v1/portal/children/{enrollment.student_id}/recommendations/"
    )

    assert response.status_code == 200
    assert response.data["recommendations"] == []


@pytest.mark.django_db
def test_student_portal_uses_bound_student_without_a_client_student_id(api_client, base_data):
    user = User.objects.create_user(
        username="portal-student", email="portal-student@example.com", password="Strong-pass-123"
    )
    StudentAccount.objects.create(
        user=user, student=base_data["students"][0], verified_at=timezone.now()
    )
    api_client.force_authenticate(user)
    response = api_client.get("/api/v1/portal/student/reports/")
    assert response.status_code == 200
    assert "student_id" not in response.request.get("QUERY_STRING", "")


@pytest.mark.django_db
def test_portal_visibility_policy_is_configurable_but_counseling_is_hard_denied(
    api_client, base_data
):
    RoleAssignment.objects.create(
        user=base_data["manager"],
        organization=base_data["organization"],
        role=Role.ORGANIZATION_ADMIN,
    )
    api_client.force_authenticate(base_data["manager"])
    headers = {"HTTP_X_ORGANIZATION_ID": str(base_data["organization"].id)}
    denied = api_client.post(
        "/api/v1/portal/visibility-policies/",
        {
            "organization": str(base_data["organization"].id),
            "resource": "counseling",
            "visibility": "visible",
        },
        format="json",
        **headers,
    )
    assert denied.status_code == 400
    assert "visibility" in denied.data["error"]["detail"]

    accepted = api_client.post(
        "/api/v1/portal/visibility-policies/",
        {
            "organization": str(base_data["organization"].id),
            "resource": "attendance_summary",
            "visibility": "hidden",
        },
        format="json",
        **headers,
    )
    assert accepted.status_code == 201

    parent = guardian_portal_user(base_data)
    api_client.force_authenticate(parent)
    response = api_client.get(f"/api/v1/portal/children/{base_data['students'][0].id}/attendance/")
    assert response.status_code == 200
    assert response.data == {
        "finalized_session_count": 0,
        "unexcused_absence_count": 0,
        "excused_absence_count": 0,
    }
