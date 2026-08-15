import pytest
from django.utils import timezone

from hamamooz.apps.accounts.models import Role, RoleAssignment, User
from hamamooz.apps.core.models import AuditEvent
from hamamooz.apps.counseling.models import CounselingCase, CounselingSession, Referral
from hamamooz.apps.guidance.models import GuideTeacherAssignment
from hamamooz.apps.students.models import Enrollment


@pytest.mark.django_db
def test_counseling_case_list_returns_only_shared_case_metadata_for_school_scope(
    api_client, base_data
):
    """A non-counselor school manager may see no private data while listing shared case metadata."""
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        "/api/v1/counseling/cases/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    assert response.data["count"] == 0
    assert response.data["results"] == []


def make_counselor(base_data, *, username="counselor", school_key="school1"):
    counselor = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="Strong-pass-123",
    )
    RoleAssignment.objects.create(
        user=counselor,
        organization=base_data["organization"],
        school=base_data[school_key],
        role=Role.COUNSELOR,
    )
    return counselor


@pytest.mark.django_db
def test_private_counseling_session_is_owner_only_and_audit_never_contains_note(
    api_client, base_data
):
    counselor = make_counselor(base_data)
    case = CounselingCase.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=base_data["enrollments"][0],
        assigned_counselor=counselor,
        opened_by=counselor,
    )
    CounselingSession.objects.create(
        case=case,
        occurred_at=timezone.now(),
        private_note="highly confidential narrative",
        recorded_by=counselor,
    )

    api_client.force_authenticate(base_data["manager"])
    manager_response = api_client.get(
        f"/api/v1/counseling/cases/{case.id}/private-sessions/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert manager_response.status_code == 403

    api_client.force_authenticate(counselor)
    response = api_client.get(
        f"/api/v1/counseling/cases/{case.id}/private-sessions/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert response.status_code == 200
    assert response.data[0]["private_note"] == "highly confidential narrative"
    audit = AuditEvent.objects.get(action="counseling.private_sessions_read")
    assert "highly confidential narrative" not in str(audit.metadata)
    assert audit.metadata == {"scope": "private_sessions", "access_reason": "assigned_counselor"}


@pytest.mark.django_db
def test_counseling_does_not_grant_global_system_admin_default_access(api_client, base_data):
    counselor = make_counselor(base_data)
    case = CounselingCase.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=base_data["enrollments"][0],
        assigned_counselor=counselor,
        opened_by=counselor,
    )
    system_admin = User.objects.create_superuser(
        username="systemadmin", email="systemadmin@example.com", password="Strong-pass-123"
    )
    api_client.force_authenticate(system_admin)

    response = api_client.get(
        f"/api/v1/counseling/cases/{case.id}/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_explicit_referral_creates_a_fresh_target_case_without_copying_private_sessions(
    api_client, base_data
):
    source_counselor = make_counselor(base_data, username="source-counselor")
    target_counselor = make_counselor(base_data, username="target-counselor", school_key="school2")
    source = CounselingCase.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=base_data["enrollments"][0],
        assigned_counselor=source_counselor,
        opened_by=source_counselor,
    )
    CounselingSession.objects.create(
        case=source,
        occurred_at=timezone.now(),
        private_note="never copy this note",
        recorded_by=source_counselor,
    )
    source_enrollment = base_data["enrollments"][0]
    source_enrollment.status = Enrollment.Status.TRANSFERRED
    source_enrollment.left_on = base_data["year"].starts_on
    source_enrollment.save(update_fields=["status", "left_on", "updated_at"])
    target_enrollment = Enrollment.objects.create(
        student=source_enrollment.student,
        school=base_data["school2"],
        academic_year=base_data["year"],
        grade_level=base_data["grade"],
        class_section=base_data["class2"],
        student_number="201",
        enrolled_on=base_data["year"].starts_on,
    )

    api_client.force_authenticate(source_counselor)
    create = api_client.post(
        f"/api/v1/counseling/cases/{source.id}/referrals/",
        {
            "target_enrollment": str(target_enrollment.id),
            "target_counselor": str(target_counselor.id),
            "purpose": "transfer hand-off",
            "handoff_summary": "explicitly approved hand-off summary",
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert create.status_code == 201

    api_client.force_authenticate(target_counselor)
    accepted = api_client.post(
        f"/api/v1/counseling/referrals/{create.data['id']}/accept/",
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school2"].id),
    )
    assert accepted.status_code == 200
    target_case = CounselingCase.objects.get(pk=accepted.data["accepted_case_id"])
    assert target_case.school_id == base_data["school2"].id
    assert target_case.sessions.count() == 0
    assert source.sessions.count() == 1


@pytest.mark.django_db
def test_guide_teacher_can_only_see_assigned_enrollment(api_client, base_data):
    guide_teacher = User.objects.create_user(
        username="guide", email="guide@example.com", password="Strong-pass-123"
    )
    RoleAssignment.objects.create(
        user=guide_teacher,
        organization=base_data["organization"],
        school=base_data["school1"],
        role=Role.GUIDE_TEACHER,
    )
    GuideTeacherAssignment.objects.create(
        enrollment=base_data["enrollments"][0],
        guide_teacher=guide_teacher,
        starts_at=base_data["year"].starts_on,
        assigned_by=base_data["manager"],
    )
    counselor = make_counselor(base_data)
    visible = CounselingCase.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=base_data["enrollments"][0],
        assigned_counselor=counselor,
        opened_by=counselor,
    )
    hidden = CounselingCase.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=base_data["enrollments"][1],
        assigned_counselor=counselor,
        opened_by=counselor,
    )
    api_client.force_authenticate(guide_teacher)
    result = api_client.get(
        "/api/v1/counseling/cases/", HTTP_X_SCHOOL_ID=str(base_data["school1"].id)
    )
    assert result.status_code == 200
    assert [row["id"] for row in result.data["results"]] == [str(visible.id)]
    forbidden = api_client.get(
        f"/api/v1/counseling/cases/{hidden.id}/private-sessions/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    # Object existence is intentionally concealed outside the guide cohort.
    assert forbidden.status_code == 404


@pytest.mark.django_db
def test_guide_teacher_student_directory_and_360_are_limited_to_their_assignment(
    api_client, base_data
):
    guide_teacher = User.objects.create_user(
        username="guide-student-access",
        email="guide-student-access@example.com",
        password="Strong-pass-123",
    )
    RoleAssignment.objects.create(
        user=guide_teacher,
        organization=base_data["organization"],
        school=base_data["school1"],
        role=Role.GUIDE_TEACHER,
    )
    GuideTeacherAssignment.objects.create(
        enrollment=base_data["enrollments"][0],
        guide_teacher=guide_teacher,
        starts_at=base_data["year"].starts_on,
        assigned_by=base_data["manager"],
    )

    api_client.force_authenticate(guide_teacher)
    headers = {"HTTP_X_SCHOOL_ID": str(base_data["school1"].id)}
    directory = api_client.get("/api/v1/students/", **headers)
    visible = api_client.get(
        f"/api/v1/students/{base_data['students'][0].id}/360/summary/", **headers
    )
    hidden = api_client.get(
        f"/api/v1/students/{base_data['students'][1].id}/360/summary/", **headers
    )

    assert directory.status_code == 200
    assert [row["id"] for row in directory.data["results"]] == [
        str(base_data["students"][0].id),
    ]
    assert visible.status_code == 200
    assert visible.data["student"]["id"] == str(base_data["students"][0].id)
    assert hidden.status_code == 404


@pytest.mark.django_db
def test_counselor_student_directory_and_360_are_limited_to_owned_cases(
    api_client, base_data
):
    counselor = make_counselor(base_data, username="counselor-student-access")
    CounselingCase.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=base_data["enrollments"][0],
        assigned_counselor=counselor,
        opened_by=counselor,
    )

    api_client.force_authenticate(counselor)
    headers = {"HTTP_X_SCHOOL_ID": str(base_data["school1"].id)}
    directory = api_client.get("/api/v1/students/", **headers)
    visible = api_client.get(
        f"/api/v1/students/{base_data['students'][0].id}/360/summary/", **headers
    )
    hidden = api_client.get(
        f"/api/v1/students/{base_data['students'][1].id}/360/summary/", **headers
    )

    assert directory.status_code == 200
    assert [row["id"] for row in directory.data["results"]] == [
        str(base_data["students"][0].id),
    ]
    assert visible.status_code == 200
    assert hidden.status_code == 404


@pytest.mark.django_db
def test_incoming_counseling_referral_grants_only_its_target_student(
    api_client, base_data
):
    source_counselor = make_counselor(base_data, username="source-referral")
    target_counselor = make_counselor(base_data, username="target-referral")
    source_case = CounselingCase.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        enrollment=base_data["enrollments"][0],
        assigned_counselor=source_counselor,
        opened_by=source_counselor,
    )
    Referral.objects.create(
        source_case=source_case,
        target_enrollment=base_data["enrollments"][0],
        target_counselor=target_counselor,
        created_by=source_counselor,
        purpose="handoff",
        status=Referral.Status.SENT,
    )

    api_client.force_authenticate(target_counselor)
    headers = {"HTTP_X_SCHOOL_ID": str(base_data["school1"].id)}
    directory = api_client.get("/api/v1/students/", **headers)
    visible = api_client.get(
        f"/api/v1/students/{base_data['students'][0].id}/360/summary/", **headers
    )
    hidden = api_client.get(
        f"/api/v1/students/{base_data['students'][1].id}/360/summary/", **headers
    )

    assert directory.status_code == 200
    assert [row["id"] for row in directory.data["results"]] == [
        str(base_data["students"][0].id),
    ]
    assert visible.status_code == 200
    assert hidden.status_code == 404


@pytest.mark.django_db
def test_guide_assignment_requires_a_real_guide_teacher_role(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])
    payload = {
        "enrollment": str(base_data["enrollments"][0].id),
        "guide_teacher": base_data["teacher1"].id,
        "starts_at": str(base_data["year"].starts_on),
    }
    headers = {"HTTP_X_SCHOOL_ID": str(base_data["school1"].id)}

    denied = api_client.post(
        "/api/v1/guide-teacher-assignments/", payload, format="json", **headers
    )
    assert denied.status_code == 400
    assert "guide_teacher" in denied.data["error"]["detail"]

    RoleAssignment.objects.create(
        user=base_data["teacher1"],
        organization=base_data["organization"],
        school=base_data["school1"],
        role=Role.GUIDE_TEACHER,
    )
    accepted = api_client.post(
        "/api/v1/guide-teacher-assignments/", payload, format="json", **headers
    )
    assert accepted.status_code == 201
