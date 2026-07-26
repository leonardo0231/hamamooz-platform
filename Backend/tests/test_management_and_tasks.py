from datetime import date
from decimal import Decimal
from io import StringIO
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from hamamooz.apps.academics.models import Assessment, Score
from hamamooz.apps.academics.services import bulk_upsert_scores
from hamamooz.apps.academics.tasks import recalculate_class_term_task
from hamamooz.apps.accounts.models import Role, RoleAssignment, User
from hamamooz.apps.attendance.models import AttendancePolicy, ParentNotification
from hamamooz.apps.attendance.tasks import (
    dispatch_parent_notification,
    evaluate_attendance_alerts,
)
from hamamooz.apps.organizations.models import ClassSection, Organization, School
from hamamooz.apps.reports.models import ReportArchive
from hamamooz.apps.reports.tasks import generate_report_task
from hamamooz.apps.students.models import Guardian


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
    assert len(list((tmp_path / "docs" / "import_templates").glob("*_template.xlsx"))) == 4


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


@pytest.mark.django_db
def test_attendance_notification_task_and_dispatch_command(base_data, settings, monkeypatch):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    guardian = Guardian.objects.create(
        organization=base_data["organization"],
        first_name="ولی",
        last_name="تسک",
        phone_primary="09123333333",
        email="task-guardian@example.com",
    )

    in_app = ParentNotification.objects.create(
        school=base_data["school1"],
        student=base_data["students"][0],
        enrollment=base_data["enrollments"][0],
        guardian=guardian,
        kind=ParentNotification.Kind.SUMMARY,
        channel=ParentNotification.Channel.IN_APP,
        recipient=str(guardian.id),
        subject="گزارش",
        message="متن گزارش",
        dedupe_key="task-in-app",
        created_by=base_data["manager"],
    )
    assert dispatch_parent_notification.run(str(in_app.id)) == str(in_app.id)
    in_app.refresh_from_db()
    assert in_app.status == ParentNotification.Status.SKIPPED
    assert dispatch_parent_notification.run(str(in_app.id)) == str(in_app.id)

    email_notification = ParentNotification.objects.create(
        school=base_data["school1"],
        student=base_data["students"][0],
        enrollment=base_data["enrollments"][0],
        guardian=guardian,
        kind=ParentNotification.Kind.SUMMARY,
        channel=ParentNotification.Channel.EMAIL,
        recipient=guardian.email,
        subject="گزارش ایمیلی",
        message="متن گزارش ایمیلی",
        dedupe_key="task-email",
        created_by=base_data["manager"],
    )
    assert dispatch_parent_notification.run(str(email_notification.id)) == str(
        email_notification.id
    )
    email_notification.refresh_from_db()
    assert email_notification.status == ParentNotification.Status.SENT
    assert email_notification.sent_at is not None

    queued = ParentNotification.objects.create(
        school=base_data["school1"],
        student=base_data["students"][1],
        enrollment=base_data["enrollments"][1],
        guardian=guardian,
        kind=ParentNotification.Kind.SUMMARY,
        channel=ParentNotification.Channel.EMAIL,
        recipient=guardian.email,
        subject="در صف",
        message="متن",
        dedupe_key="dispatch-command-queued",
        created_by=base_data["manager"],
    )
    delayed_ids = []
    monkeypatch.setattr(
        "hamamooz.apps.attendance.management.commands.dispatch_attendance_notifications."
        "dispatch_parent_notification.delay",
        lambda notification_id: delayed_ids.append(notification_id),
    )
    output = StringIO()
    call_command("dispatch_attendance_notifications", limit=1, stdout=output)
    assert delayed_ids == [str(queued.id)]
    assert "1 اعلان" in output.getvalue()


@pytest.mark.django_db
def test_attendance_alert_task_and_management_command(base_data, settings):
    policy = AttendancePolicy.objects.create(
        school=base_data["school1"],
        academic_year=base_data["year"],
        warning_absence_count=10,
        critical_absence_count=20,
        notify_guardians=False,
    )

    assert evaluate_attendance_alerts.run(str(policy.id)) == []

    settings.ATTENDANCE_AUTO_ALERTS_ENABLED = False
    assert evaluate_attendance_alerts.run() == []
    settings.ATTENDANCE_AUTO_ALERTS_ENABLED = True

    output = StringIO()
    call_command(
        "evaluate_attendance_alerts",
        policy_id=str(policy.id),
        stdout=output,
    )
    assert "0 هشدار فعال" in output.getvalue()

    with pytest.raises(CommandError):
        call_command(
            "evaluate_attendance_alerts",
            policy_id=str(uuid4()),
            verbosity=0,
        )
