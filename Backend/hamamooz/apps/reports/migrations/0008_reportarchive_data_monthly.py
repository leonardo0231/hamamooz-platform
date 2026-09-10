from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0007_normalize_report_page_size"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reportarchive",
            name="term",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="reports",
                to="organizations.term",
            ),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="report_mode",
            field=models.CharField(
                choices=[
                    ("official_term", "کارنامه رسمی نوبت"),
                    ("data_monthly", "کارنامه داده‌محور ماهانه"),
                ],
                db_index=True,
                default="official_term",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="month_no",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(1), MaxValueValidator(12)],
            ),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="month_title",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="source_file",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="source_row",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="reportarchive",
            index=models.Index(
                fields=["enrollment", "report_mode", "month_no"],
                name="reports_enrol_mode_mon_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="reportarchive",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(report_mode="official_term", term__isnull=False, month_no__isnull=True)
                    | models.Q(report_mode="data_monthly", term__isnull=True, month_no__isnull=False)
                ),
                name="ck_report_archive_mode_period",
            ),
        ),
    ]
