import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0002_term_summer"),
        ("evaluations", "0002_alter_monthlyevaluation_framework_version"),
    ]

    operations = [
        migrations.AddField(
            model_name="monthlyevaluation",
            name="term",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="monthly_evaluations",
                to="organizations.term",
            ),
        ),
        migrations.AddField(
            model_name="monthlyevaluation",
            name="raw_metric_values",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="monthlyevaluation",
            name="source_summary",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
