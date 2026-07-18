from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from hamamooz.apps.academics.models import Assessment, Score
from hamamooz.apps.academics.services import bulk_upsert_scores
from hamamooz.apps.academics.tasks import recalculate_class_term_task
from hamamooz.apps.accounts.models import Role, RoleAssignment, User
from hamamooz.apps.organizations.models import ClassSection, Organization, School
from hamamooz.apps.reports.models import ReportArchive
from hamamooz.apps.reports.tasks import generate_report_task


@pytest.mark.django_db
def test_seed_demo_is_idempotent_and_generates_all_import_templates(settings, tmp_path):
    settings.BASE_DIR = tmp_path

    call_command(
        "seed_demo",
        admin_username="seed-admin",
        admin_email="seed-admin@example.com",
        admin_password="Strong-seed-pass-123",
        verbosity=0,
    )
    call_command(
        "seed_demo",
        admin_username="seed-admin",
        admin_email="seed-admin@example.com",
        admin_password="Strong-seed-pass-123",
        verbosity=0,
    )

    organization = Organization.objects.get(code="hamamooz")
    admin = User.objects.get(username="seed-admin")
    assert School.objects.filter(organization=organization).count() == 13
    assert ClassSection.objects.filter(school__organization=organization).count() == 13
    assert RoleAssignment.objects.filter(user=admin, role=Role.SYSTEM_ADMIN).count() == 1
    assert len(list((tmp_path / "docs" / "import_templates").glob("*_template.xlsx"))) == 3


@pytest.mark.django_db
def test_seed_demo_requires_explicit_admin_password():
    with pytest.raises(CommandError):
        call_command("seed_demo", admin_password=None, verbosity=0)


@pytest.mark.django_db
def test_calculation_and_report_tasks_return_serializable_results(base_data, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    assessment = Assessment.objects.create(
        course_offering=base_data["offering1"],
        assessment_type=base_data["final"],
        title="Task report",
        assessment_date=date(2026, 12, 20),
        max_score=Decimal("20"),
        created_by=base_data["teacher1"],
    )
    bulk_upsert_scores(
        assessment=assessment,
        entries=[
            {
                "enrollment": enrollment,
                "value": Decimal("18"),
                "status": Score.Status.PRESENT,
            }
            for enrollment in base_data["enrollments"]
        ],
        actor=base_data["teacher1"],
    )
    assessment.status = Assessment.Status.LOCKED
    assessment.save(update_fields=["status"])

    calculation = recalculate_class_term_task.run(
        str(base_data["class1"].id), str(base_data["term"].id)
    )
    assert calculation == {"calculated": 2}

    report = ReportArchive.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        term=base_data["term"],
        report_type=ReportArchive.ReportType.STUDENT_REPORT_CARD,
        enrollment=base_data["enrollments"][0],
        requested_by=base_data["manager"],
    )
    generated = generate_report_task.run(str(report.id))
    assert generated["status"] == ReportArchive.Status.COMPLETED
    assert generated["file"].endswith(".pdf")
