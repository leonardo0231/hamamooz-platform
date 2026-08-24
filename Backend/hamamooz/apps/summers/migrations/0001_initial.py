import uuid
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("academics", "0004_active_policy_scope"),
        ("organizations", "0001_initial"),
        ("students", "0004_guardianaccount_studentaccount"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SummerProgram",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("title", models.CharField(max_length=150)),
                (
                    "pass_threshold",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=4,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0")),
                            django.core.validators.MaxValueValidator(Decimal("20")),
                        ],
                    ),
                ),
                (
                    "academic_year",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="summer_programs",
                        to="organizations.academicyear",
                    ),
                ),
                (
                    "school",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="summer_programs",
                        to="organizations.school",
                    ),
                ),
            ],
            options={
                "ordering": ["-academic_year__starts_on", "school", "title"],
                "indexes": [
                    models.Index(
                        fields=["school", "academic_year", "is_deleted"],
                        name="summers_sum_school__c0aa1e_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("is_deleted", False)),
                        fields=("school", "academic_year"),
                        name="uq_active_summer_program_school_year",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(pass_threshold__isnull=True)
                        | models.Q(pass_threshold__gte=0, pass_threshold__lte=20),
                        name="ck_summer_program_threshold_0_20",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="SummerCourse",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="courses",
                        to="summers.summerprogram",
                    ),
                ),
                (
                    "subject",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="summer_courses",
                        to="academics.subject",
                    ),
                ),
            ],
            options={
                "ordering": ["program", "subject__title"],
                "indexes": [
                    models.Index(
                        fields=["program", "is_deleted"], name="summers_sum_program_53fda3_idx"
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("is_deleted", False)),
                        fields=("program", "subject"),
                        name="uq_active_summer_course_program_subject",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="SummerRegistration",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="summer_registrations",
                        to="students.enrollment",
                    ),
                ),
                (
                    "program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registrations",
                        to="summers.summerprogram",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "program",
                    "enrollment__student__last_name",
                    "enrollment__student__first_name",
                ],
                "indexes": [
                    models.Index(
                        fields=["program", "is_deleted"], name="summers_sum_program_c91a73_idx"
                    ),
                    models.Index(
                        fields=["enrollment", "is_deleted"],
                        name="summers_sum_enrollm_5bec47_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("is_deleted", False)),
                        fields=("program", "enrollment"),
                        name="uq_active_summer_registration_program_enrollment",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="SummerComprehensiveExam",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("title", models.CharField(max_length=150)),
                ("exam_date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "پیش‌نویس"), ("finalized", "نهایی‌شده")],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                (
                    "finalized_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="finalized_summer_exams",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="exams",
                        to="summers.summerprogram",
                    ),
                ),
            ],
            options={
                "ordering": ["-exam_date", "title"],
                "indexes": [
                    models.Index(
                        fields=["program", "status", "is_deleted"],
                        name="summers_sum_program_6d1055_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("is_deleted", False)),
                        fields=("program",),
                        name="uq_active_summer_exam_program",
                    ),
                    models.CheckConstraint(
                        condition=(
                            ~models.Q(status="finalized")
                            | models.Q(
                                finalized_at__isnull=False,
                                finalized_by__isnull=False,
                            )
                        ),
                        name="ck_summer_exam_finalized_evidence",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="SummerProgramRevision",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "old_pass_threshold",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=4,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0")),
                            django.core.validators.MaxValueValidator(Decimal("20")),
                        ],
                    ),
                ),
                (
                    "new_pass_threshold",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=4,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0")),
                            django.core.validators.MaxValueValidator(Decimal("20")),
                        ],
                    ),
                ),
                ("reason", models.CharField(max_length=500)),
                (
                    "actor",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="summer_program_revisions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="threshold_revisions",
                        to="summers.summerprogram",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(old_pass_threshold__isnull=True)
                        | models.Q(
                            old_pass_threshold__gte=0,
                            old_pass_threshold__lte=20,
                        ),
                        name="ck_summer_revision_old_threshold_0_20",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(new_pass_threshold__isnull=True)
                        | models.Q(
                            new_pass_threshold__gte=0,
                            new_pass_threshold__lte=20,
                        ),
                        name="ck_summer_revision_new_threshold_0_20",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="SummerCourseRegistration",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registrations",
                        to="summers.summercourse",
                    ),
                ),
                (
                    "registration",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="course_registrations",
                        to="summers.summerregistration",
                    ),
                ),
            ],
            options={
                "ordering": ["registration", "course__subject__title"],
                "indexes": [
                    models.Index(
                        fields=["registration", "is_deleted"],
                        name="summers_sum_registr_9440ef_idx",
                    ),
                    models.Index(
                        fields=["course", "is_deleted"], name="summers_sum_course__fb2f5d_idx"
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("is_deleted", False)),
                        fields=("registration", "course"),
                        name="uq_active_summer_course_registration",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="SummerSubjectScore",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "value",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=4,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0")),
                            django.core.validators.MaxValueValidator(Decimal("20")),
                        ],
                    ),
                ),
                (
                    "course_registration",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subject_scores",
                        to="summers.summercourseregistration",
                    ),
                ),
                (
                    "exam",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subject_scores",
                        to="summers.summercomprehensiveexam",
                    ),
                ),
                (
                    "recorded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="recorded_summer_scores",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": [
                    "course_registration__registration__enrollment__student__last_name",
                    "course_registration__course__subject__title",
                ],
                "indexes": [
                    models.Index(
                        fields=["exam", "course_registration"],
                        name="summers_sum_exam_id_3a3887_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("exam", "course_registration"),
                        name="uq_summer_score_exam_course_registration",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("value__gte", 0), ("value__lte", 20)),
                        name="ck_summer_subject_score_0_20",
                    ),
                ],
            },
        ),
    ]
