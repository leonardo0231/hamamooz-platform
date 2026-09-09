import django.db.models.deletion
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
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reports",
                to="organizations.term",
            ),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="report_mode",
            field=models.CharField(
                choices=[
                    ("official_term", "نوبت رسمی"),
                    ("data_monthly", "گزارش ماهانه مسیر Data"),
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
        migrations.AlterField(
            model_name="reportbatch",
            name="term",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="report_batches",
                to="organizations.term",
            ),
        ),
        migrations.AddField(
            model_name="reportbatch",
            name="report_mode",
            field=models.CharField(
                choices=[
                    ("official_term", "نوبت رسمی"),
                    ("data_monthly", "گزارش ماهانه مسیر Data"),
                ],
                db_index=True,
                default="official_term",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="reportbatch",
            name="month_no",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(1), MaxValueValidator(12)],
            ),
        ),
    ]
