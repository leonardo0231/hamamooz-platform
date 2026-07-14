import os
from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hamamooz.apps.academics.models import (
    AssessmentType,
    CalculationPolicy,
    GradeSubject,
    Subject,
)
from hamamooz.apps.accounts.models import Role, RoleAssignment, User
from hamamooz.apps.organizations.models import (
    AcademicYear,
    ClassSection,
    GradeLevel,
    Organization,
    School,
    Term,
)


class Command(BaseCommand):
    help = "Create an idempotent 13-branch HamAmoz MVP demo structure."

    def add_arguments(self, parser):
        parser.add_argument("--admin-username", default="admin")
        parser.add_argument("--admin-email", default="admin@example.com")
        parser.add_argument("--admin-password", default=os.getenv("SEED_ADMIN_PASSWORD"))

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["admin_password"]
        if not password:
            raise CommandError("Use --admin-password or set SEED_ADMIN_PASSWORD.")

        organization, _ = Organization.objects.get_or_create(
            code="hamamooz",
            defaults={"name": "مجموعه آموزشی هم‌آموز"},
        )
        schools = []
        for index in range(1, 14):
            school, _ = School.objects.get_or_create(
                organization=organization,
                code=f"branch-{index:02d}",
                defaults={"name": f"شعبه {index}", "official_name": f"مدرسه هم‌آموز - شعبه {index}"},
            )
            schools.append(school)

        year, _ = AcademicYear.objects.get_or_create(
            organization=organization,
            code="1405-1406",
            defaults={
                "title": "۱۴۰۵-۱۴۰۶",
                "starts_on": date(2026, 9, 23),
                "ends_on": date(2027, 6, 22),
                "is_current": True,
            },
        )
        term1, _ = Term.objects.get_or_create(
            academic_year=year,
            code=Term.Code.FIRST,
            defaults={
                "title": "نوبت اول",
                "starts_on": date(2026, 9, 23),
                "ends_on": date(2027, 1, 20),
                "order": 1,
            },
        )
        Term.objects.get_or_create(
            academic_year=year,
            code=Term.Code.SECOND,
            defaults={
                "title": "نوبت دوم",
                "starts_on": date(2027, 1, 21),
                "ends_on": date(2027, 6, 22),
                "order": 2,
            },
        )
        grades = {}
        for order in range(1, 13):
            grade, _ = GradeLevel.objects.get_or_create(
                organization=organization,
                code=f"grade-{order}",
                defaults={"title": f"پایه {order}", "order": order},
            )
            grades[order] = grade
        for school in schools:
            ClassSection.objects.get_or_create(
                school=school,
                academic_year=year,
                grade_level=grades[7],
                code="7-a",
                defaults={"title": "هفتم الف", "capacity": 35},
            )

        for code, title, coefficient in [
            ("math", "ریاضی", "3"),
            ("science", "علوم", "2"),
            ("persian", "فارسی", "2"),
            ("english", "زبان انگلیسی", "1"),
        ]:
            subject, _ = Subject.objects.get_or_create(
                organization=organization,
                code=code,
                defaults={"title": title, "default_coefficient": Decimal(coefficient)},
            )
            GradeSubject.objects.get_or_create(
                grade_level=grades[7],
                subject=subject,
                defaults={"coefficient": Decimal(coefficient), "pass_mark": Decimal("10")},
            )

        for code, title, category, weight in [
            ("continuous", "مستمر", "continuous", "1"),
            ("midterm", "میان‌ترم", "midterm", "1"),
            ("final", "پایانی", "final", "2"),
        ]:
            AssessmentType.objects.get_or_create(
                organization=organization,
                code=code,
                defaults={"title": title, "category": category, "default_weight": Decimal(weight)},
            )
        CalculationPolicy.objects.get_or_create(
            organization=organization,
            academic_year=year,
            grade_level=None,
            version="mvp-1405-v1",
            defaults={"title": "فرمول استاندارد MVP", "overall_pass_mark": Decimal("10")},
        )

        admin, created = User.objects.get_or_create(
            username=options["admin_username"],
            defaults={
                "email": options["admin_email"],
                "first_name": "مدیر",
                "last_name": "سامانه",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password(password)
            admin.save(update_fields=["password"])
        RoleAssignment.objects.get_or_create(
            user=admin,
            organization=None,
            school=None,
            role=Role.SYSTEM_ADMIN,
        )
        call_command("generate_import_templates")
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {organization.name}, {len(schools)} schools, "
                f"year {year}, term {term1}."
            )
        )
