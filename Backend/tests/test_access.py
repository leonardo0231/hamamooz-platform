import pytest

from hamamooz.apps.academics.models import Assessment


@pytest.mark.django_db
def test_teacher_only_sees_own_course_offerings(api_client, base_data):
    api_client.force_authenticate(base_data["teacher1"])
    response = api_client.get(
        "/api/v1/course-offerings/", HTTP_X_SCHOOL_ID=str(base_data["school1"].id)
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.data["results"]}
    assert ids == {str(base_data["offering1"].id)}


@pytest.mark.django_db
def test_teacher_cannot_select_unassigned_school(api_client, base_data):
    api_client.force_authenticate(base_data["teacher1"])
    response = api_client.get("/api/v1/students/", HTTP_X_SCHOOL_ID=str(base_data["school2"].id))
    assert response.status_code == 403


@pytest.mark.django_db
def test_teacher_cannot_create_assessment_for_another_teacher(api_client, base_data):
    api_client.force_authenticate(base_data["teacher1"])
    response = api_client.post(
        "/api/v1/assessments/",
        {
            "course_offering": str(base_data["offering2"].id),
            "assessment_type": str(base_data["continuous"].id),
            "title": "مستمر اول",
            "assessment_date": "2026-10-10",
            "max_score": "20",
            "weight": "1",
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert response.status_code in {400, 403}
    assert Assessment.objects.count() == 0


@pytest.mark.django_db
def test_teacher_user_list_does_not_leak_branch_users(api_client, base_data):
    api_client.force_authenticate(base_data["teacher1"])
    response = api_client.get("/api/v1/users/")
    assert response.status_code == 200
    assert [item["username"] for item in response.data["results"]] == ["teacher1"]


@pytest.mark.django_db
def test_users_cannot_be_deleted_and_must_be_deactivated(api_client, base_data):
    api_client.force_authenticate(base_data["manager"])
    response = api_client.delete(
        f"/api/v1/users/{base_data['teacher1'].id}/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert response.status_code == 405
