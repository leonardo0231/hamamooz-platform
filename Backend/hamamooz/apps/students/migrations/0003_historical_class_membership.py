from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("students", "0002_remove_enrollment_uq_enrollment_student_year_school")]

    operations = [
        migrations.RemoveConstraint(
            model_name="enrollment",
            name="uq_student_number_school_year",
        ),
        migrations.AddConstraint(
            model_name="enrollment",
            constraint=models.UniqueConstraint(
                fields=("school", "academic_year", "student_number"),
                condition=models.Q(status="active", is_deleted=False),
                name="uq_active_student_number_school_year",
            ),
        ),
    ]
