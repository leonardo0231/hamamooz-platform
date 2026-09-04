from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("evaluations", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="monthlyevaluation",
            name="framework_version",
            field=models.CharField(default="2.0", max_length=20),
        ),
    ]
