import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


LAYOUT_CHOICES = [
    ("analytical_term_1", "کارنامه تحلیلی نوبت اول"),
    ("analytical_term_2", "کارنامه تحلیلی نوبت دوم"),
    ("analytical_annual", "کارنامه تحلیلی سالانه"),
    ("final_term_1", "کارنامه نهایی نوبت اول"),
    ("final_term_2", "کارنامه نهایی نوبت دوم"),
    ("final_annual", "کارنامه نهایی سالانه"),
    ("summer_report", "کارنامه تابستان"),
]


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0004_reportarchive_output_format"),
        ("summers", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
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
        migrations.AlterField(
            model_name="reportdraft",
            name="term",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="report_drafts",
                to="organizations.term",
            ),
        ),
        migrations.AddField(
            model_name="reporttemplate",
            name="layout_key",
            field=models.CharField(blank=True, choices=LAYOUT_CHOICES, max_length=40),
        ),
        migrations.AddField(
            model_name="reportdraft",
            name="layout_key",
            field=models.CharField(blank=True, choices=LAYOUT_CHOICES, max_length=40),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="layout_key",
            field=models.CharField(blank=True, choices=LAYOUT_CHOICES, max_length=40),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="editable_output_file",
            field=models.FileField(blank=True, upload_to="reports/%Y/%m/"),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="source_fingerprint",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="tracking_code",
            field=models.CharField(blank=True, max_length=40, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="report_version",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="approved_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="approved_report_archives",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="reportdraft",
            name="source_fingerprint",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="reportdraft",
            name="tracking_code",
            field=models.CharField(blank=True, max_length=40, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="reportdraft",
            name="report_version",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="summer_program",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="report_archives",
                to="summers.summerprogram",
            ),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="summer_registration",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="report_archives",
                to="summers.summerregistration",
            ),
        ),
        migrations.AddField(
            model_name="reportarchive",
            name="summer_exam",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="report_archives",
                to="summers.summercomprehensiveexam",
            ),
        ),
        migrations.AddField(
            model_name="reportdraft",
            name="summer_program",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="report_drafts",
                to="summers.summerprogram",
            ),
        ),
        migrations.AddField(
            model_name="reportdraft",
            name="summer_registration",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="report_drafts",
                to="summers.summerregistration",
            ),
        ),
        migrations.AddField(
            model_name="reportdraft",
            name="summer_exam",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="report_drafts",
                to="summers.summercomprehensiveexam",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="reportdraft",
            name="ck_report_draft_exactly_one_subject_scope",
        ),
        migrations.AddConstraint(
            model_name="reportdraft",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        enrollment__isnull=False,
                        class_section__isnull=True,
                        summer_registration__isnull=True,
                    )
                    | models.Q(
                        enrollment__isnull=True,
                        class_section__isnull=False,
                        summer_registration__isnull=True,
                    )
                    | models.Q(
                        enrollment__isnull=True,
                        class_section__isnull=True,
                        summer_registration__isnull=False,
                    )
                ),
                name="ck_report_draft_exactly_one_subject_scope",
            ),
        ),
        migrations.AddIndex(
            model_name="reportarchive",
            index=models.Index(
                fields=["school", "academic_year", "layout_key", "report_version"],
                name="reports_card_scope_version_idx",
            ),
        ),
    ]
