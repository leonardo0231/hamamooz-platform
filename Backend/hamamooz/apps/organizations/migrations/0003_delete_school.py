from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_alter_roleassignment_school"),
        ("activities", "0002_alter_activity_school"),
        ("analytics", "0002_alter_analyticsrun_school_and_more"),
        ("attendance", "0003_alter_attendancealert_school_and_more"),
        ("behavior", "0002_alter_behaviorevent_school"),
        ("counseling", "0002_alter_counselingcase_school"),
        ("imports", "0009_alter_classsourceselection_school_and_more"),
        ("organizations", "0002_remove_school_organization_alter_classsection_school_and_more"),
        ("recommendations", "0002_alter_recommendation_school"),
        ("reports", "0009_alter_reportarchive_school_alter_reportbatch_school_and_more"),
        ("students", "0006_alter_enrollment_school"),
    ]

    operations = [
        migrations.DeleteModel(name="School"),
    ]
