import uuid
from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0004_active_policy_scope"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="termresult",
            name="class_population",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="termresult",
            name="grade_population",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="termresult",
            name="grade_rank",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="termresult",
            name="school_population",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="termresult",
            name="school_rank",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="AcademicReportSettings",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "first_term_weight",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("1"), max_digits=7
                    ),
                ),
                (
                    "second_term_weight",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("2"), max_digits=7
                    ),
                ),
                ("show_class_rank", models.BooleanField(default=True)),
                ("show_grade_rank", models.BooleanField(default=True)),
                ("show_school_rank", models.BooleanField(default=True)),
                ("revision", models.PositiveIntegerField(default=1)),
                (
                    "academic_year",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="academic_report_settings",
                        to="organizations.academicyear",
                    ),
                ),
                (
                    "school",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="academic_report_settings",
                        to="organizations.school",
                    ),
                ),
            ],
            options={
                "ordering": ["school", "-academic_year__starts_on"],
                "indexes": [
                    models.Index(
                        fields=["school", "academic_year"],
                        name="acad_report_school_year_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("is_deleted", False)),
                        fields=("school", "academic_year"),
                        name="uq_academic_report_settings_school_year",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("first_term_weight__gt", 0)),
                        name="ck_academic_report_first_weight_positive",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("second_term_weight__gt", 0)),
                        name="ck_academic_report_second_weight_positive",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="AnnualResult",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "average",
                    models.DecimalField(
                        blank=True, decimal_places=4, max_digits=7, null=True
                    ),
                ),
                ("class_rank", models.PositiveIntegerField(blank=True, null=True)),
                ("grade_rank", models.PositiveIntegerField(blank=True, null=True)),
                ("school_rank", models.PositiveIntegerField(blank=True, null=True)),
                ("class_population", models.PositiveIntegerField(blank=True, null=True)),
                ("grade_population", models.PositiveIntegerField(blank=True, null=True)),
                ("school_population", models.PositiveIntegerField(blank=True, null=True)),
                ("complete", models.BooleanField(default=False)),
                ("passed", models.BooleanField(default=False)),
                ("formula_version", models.CharField(max_length=30)),
                ("calculated_at", models.DateTimeField(auto_now=True)),
                (
                    "enrollment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="annual_result",
                        to="students.enrollment",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "enrollment__student__last_name",
                    "enrollment__student__first_name",
                ],
                "indexes": [
                    models.Index(fields=["average"], name="acad_annual_average_idx")
                ],
            },
        ),
        migrations.CreateModel(
            name="AcademicReportSettingsRevision",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("revision", models.PositiveIntegerField()),
                ("reason", models.TextField()),
                ("before", models.JSONField(default=dict)),
                ("after", models.JSONField(default=dict)),
                (
                    "academic_year",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="academic_report_settings_revisions",
                        to="organizations.academicyear",
                    ),
                ),
                (
                    "changed_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="academic_report_settings_revisions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "report_settings",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="history",
                        to="academics.academicreportsettings",
                    ),
                ),
                (
                    "school",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="academic_report_settings_revisions",
                        to="organizations.school",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["report_settings", "-created_at"],
                        name="acad_report_revision_time_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("report_settings", "revision"),
                        name="uq_academic_report_settings_revision",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="AnnualSubjectResult",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "average",
                    models.DecimalField(
                        blank=True, decimal_places=4, max_digits=7, null=True
                    ),
                ),
                ("complete", models.BooleanField(default=False)),
                ("passed", models.BooleanField(default=False)),
                ("formula_version", models.CharField(max_length=30)),
                ("calculated_at", models.DateTimeField(auto_now=True)),
                (
                    "annual_result",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subject_results",
                        to="academics.annualresult",
                    ),
                ),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="annual_subject_results",
                        to="students.enrollment",
                    ),
                ),
                (
                    "grade_subject",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="annual_subject_results",
                        to="academics.gradesubject",
                    ),
                ),
            ],
            options={
                "ordering": ["grade_subject__subject__title"],
                "indexes": [
                    models.Index(
                        fields=["annual_result", "grade_subject"],
                        name="acad_annual_subject_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("enrollment", "grade_subject"),
                        name="uq_annual_subject_result_enrollment_subject",
                    )
                ],
            },
        ),
    ]
