from django.db import migrations, models


def deactivate_duplicate_active_policies(apps, schema_editor):
    Policy = apps.get_model("academics", "CalculationPolicy")
    rows = Policy._base_manager.using(schema_editor.connection.alias).filter(
        is_deleted=False, is_active=True
    ).order_by("-created_at", "-pk")
    seen = set()
    deactivate = []
    for row in rows.iterator():
        key = (row.organization_id, row.academic_year_id, row.grade_level_id)
        if key in seen:
            deactivate.append(row.pk)
        else:
            seen.add(key)
    if deactivate:
        Policy._base_manager.using(schema_editor.connection.alias).filter(
            pk__in=deactivate
        ).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [("academics", "0003_remove_calculationpolicy_uq_calculation_policy_scope_version_and_more")]

    operations = [
        migrations.RunPython(deactivate_duplicate_active_policies, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="calculationpolicy",
            constraint=models.UniqueConstraint(
                fields=("organization",),
                condition=models.Q(
                    academic_year__isnull=True,
                    grade_level__isnull=True,
                    is_active=True,
                    is_deleted=False,
                ),
                name="uq_active_calc_policy_org_scope",
            ),
        ),
        migrations.AddConstraint(
            model_name="calculationpolicy",
            constraint=models.UniqueConstraint(
                fields=("organization", "academic_year"),
                condition=models.Q(
                    academic_year__isnull=False,
                    grade_level__isnull=True,
                    is_active=True,
                    is_deleted=False,
                ),
                name="uq_active_calc_policy_year_scope",
            ),
        ),
        migrations.AddConstraint(
            model_name="calculationpolicy",
            constraint=models.UniqueConstraint(
                fields=("organization", "grade_level"),
                condition=models.Q(
                    academic_year__isnull=True,
                    grade_level__isnull=False,
                    is_active=True,
                    is_deleted=False,
                ),
                name="uq_active_calc_policy_grade_scope",
            ),
        ),
        migrations.AddConstraint(
            model_name="calculationpolicy",
            constraint=models.UniqueConstraint(
                fields=("organization", "academic_year", "grade_level"),
                condition=models.Q(
                    academic_year__isnull=False,
                    grade_level__isnull=False,
                    is_active=True,
                    is_deleted=False,
                ),
                name="uq_active_calc_policy_full_scope",
            ),
        ),
    ]
