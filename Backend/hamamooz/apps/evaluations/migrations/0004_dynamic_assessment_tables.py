from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0003_dynamic_assessment_foundation"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssessmentPeriod",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=100)),
                ("period_type", models.CharField(default="custom", max_length=20)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assessment_periods", to="organizations.academicyear")),
            ],
            options={"ordering": ["order", "title"]},
        ),
        migrations.CreateModel(
            name="Indicator",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=50, unique=True)),
                ("title", models.CharField(max_length=255)),
                ("category", models.CharField(blank=True, max_length=100)),
                ("indicator_type", models.CharField(default="score", max_length=50)),
                ("max_score", models.DecimalField(decimal_places=2, default=5, max_digits=6)),
                ("weight", models.DecimalField(decimal_places=2, default=1, max_digits=6)),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="AssessmentRecord",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("score", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("indicator", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="records", to="evaluations.indicator")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="records", to="evaluations.assessmentperiod")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assessment_records", to="students.student")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
