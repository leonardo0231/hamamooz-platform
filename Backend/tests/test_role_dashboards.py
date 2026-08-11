from datetime import date

import pytest

from hamamooz.apps.accounts.models import Role, RoleAssignment, User
from hamamooz.apps.core.models import AuditEvent
from hamamooz.apps.counseling.models import CounselingCase
from hamamooz.apps.guidance.models import GuideTeacherAssignment


@pytest.mark.django_db
def test_role_dashboards_are_read_compositions_with_scoped_access(api_client, base_data):
    school = base_data["school1"]
    headers = {"HTTP_X_SCHOOL_ID": str(school.id)}

    api_client.force_authenticate(base_data["manager"])
    for endpoint, dashboard in [
        ("/api/v1/dashboard/manager/", "manager"),
        ("/api/v1/dashboard/educational/", "educational"),
        ("/api/v1/dashboard/student-affairs/", "student-affairs"),
    ]:
        response = api_client.get(endpoint, **headers)
        assert response.status_code == 200
        assert response.data["dashboard"] == dashboard
        assert response.data["scope_school_ids"] == [str(school.id)]
        assert isinstance(response.data["metrics"], dict)

    api_client.force_authenticate(base_data["teacher1"])
    response = api_client.get("/api/v1/dashboard/teacher/", **headers)
    assert response.status_code == 200
    assert response.data["dashboard"] == "teacher"


@pytest.mark.django_db
def test_student_affairs_dashboard_requires_its_explicit_school_assignment(api_client, base_data):
    """Student-affairs access is additive, not a generic academic broad scope."""

    school = base_data["school1"]
    other_school = base_data["school2"]
    user = User.objects.create_user(
        username="student-affairs-dashboard",
        email="student-affairs-dashboard@example.com",
        password="Strong-pass-123",
    )
    RoleAssignment.objects.create(
        user=user,
        organization=base_data["organization"],
        school=school,
        role=Role.STUDENT_AFFAIRS_DEPUTY,
    )

    api_client.force_authenticate(user)
    response = api_client.get("/api/v1/dashboard/student-affairs/", HTTP_X_SCHOOL_ID=str(school.id))

    assert response.status_code == 200
    assert response.data["dashboard"] == "student-affairs"
    assert response.data["scope_school_ids"] == [str(school.id)]
    denied = api_client.get(
        "/api/v1/dashboard/student-affairs/", HTTP_X_SCHOOL_ID=str(other_school.id)
    )
    assert denied.status_code == 403


@pytest.mark.django_db
def test_confidential_and_guide_dashboards_require_direct_assignment_and_never_return_notes(
    api_client, base_data
):
    school = base_data["school1"]
    organization = base_data["organization"]
    headers = {"HTTP_X_SCHOOL_ID": str(school.id), "HTTP_X_REQUEST_ID": "role-dashboard-test"}

    counselor = User.objects.create_user(
        username="counselor-dashboard",
        email="counselor-dashboard@example.com",
        password="Strong-pass-123",
    )
    guide_teacher = User.objects.create_user(
        username="guide-dashboard", email="guide-dashboard@example.com", password="Strong-pass-123"
    )
    RoleAssignment.objects.create(
        user=counselor, organization=organization, school=school, role=Role.COUNSELOR
    )
    RoleAssignment.objects.create(
        user=guide_teacher, organization=organization, school=school, role=Role.GUIDE_TEACHER
    )
    CounselingCase.objects.create(
        organization=organization,
        school=school,
        enrollment=base_data["enrollments"][0],
        assigned_counselor=counselor,
        opened_by=counselor,
        status=CounselingCase.Status.ACTIVE,
        shared_risk_level=CounselingCase.RiskLevel.HIGH,
    )
    GuideTeacherAssignment.objects.create(
        enrollment=base_data["enrollments"][0],
        guide_teacher=guide_teacher,
        assigned_by=base_data["manager"],
        starts_at=date(2026, 9, 23),
    )

    api_client.force_authenticate(counselor)
    counselor_response = api_client.get("/api/v1/dashboard/counselor/", **headers)
    assert counselor_response.status_code == 200
    assert counselor_response.data["metrics"]["active_assigned_cases"] == 1
    assert "private_note" not in str(counselor_response.data)
    audit = AuditEvent.objects.get(action="counseling.dashboard_viewed")
    assert audit.request_id == "role-dashboard-test"
    assert "private_note" not in str(audit.metadata)

    api_client.force_authenticate(guide_teacher)
    guide_response = api_client.get("/api/v1/dashboard/guide-teacher/", **headers)
    assert guide_response.status_code == 200
    assert guide_response.data["metrics"]["active_assignments"] == 1

    api_client.force_authenticate(base_data["manager"])
    assert api_client.get("/api/v1/dashboard/counselor/", **headers).status_code == 403
    assert api_client.get("/api/v1/dashboard/guide-teacher/", **headers).status_code == 403
