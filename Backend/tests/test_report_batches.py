import pytest

from hamamooz.apps.reports.models import ReportBatch
from hamamooz.apps.students.models import student_photo_upload_to


@pytest.mark.django_db
def test_authorized_manager_can_queue_a_class_report_batch(api_client, base_data, monkeypatch):
    api_client.force_authenticate(base_data["manager"])
    monkeypatch.setattr(
        "hamamooz.apps.reports.views.generate_report_batch_task.delay", lambda *args: None
    )
    monkeypatch.setattr(
        "hamamooz.apps.reports.serializers.validate_official_report_readiness", lambda attrs: attrs
    )
    response = api_client.post(
        "/api/v1/reports/batches/",
        {
            "school": str(base_data["school1"].id),
            "academic_year": str(base_data["year"].id),
            "term": str(base_data["term"].id),
            "scope": "class",
            "class_section": str(base_data["class1"].id),
            "page_size": "a3_landscape",
        },
        format="json",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )
    assert response.status_code == 201
    assert response.data["total_count"] == len(base_data["enrollments"])
    assert ReportBatch.objects.get(pk=response.data["id"]).items.count() == len(
        base_data["enrollments"]
    )


@pytest.mark.django_db
def test_student_photo_path_is_organization_scoped_and_national_id_based(base_data):
    student = base_data["students"][0]
    path = student_photo_upload_to(student, "portrait.PNG")
    assert str(student.organization_id) in path
    assert student.national_id in path
    assert path.endswith(".png")
