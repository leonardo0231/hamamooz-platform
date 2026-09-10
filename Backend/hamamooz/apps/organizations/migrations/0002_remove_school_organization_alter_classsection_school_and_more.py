from collections import defaultdict

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


BESAT_CODE = "besat"
BESAT_NAME = "بعثت"
BESAT_OFFICIAL_NAME = "مدرسه بعثت"

SCHOOL_REFERENCES = (
    ("organizations", "ClassSection"),
    ("accounts", "RoleAssignment"),
    ("students", "Enrollment"),
    ("imports", "ImportJob"),
    ("imports", "DataSourceManifest"),
    ("imports", "ClassSourceSelection"),
    ("imports", "DataSourceConflict"),
    ("reports", "ReportArchive"),
    ("reports", "ReportBatch"),
    ("reports", "ReportTemplate"),
    ("reports", "ReportDraft"),
    ("attendance", "AttendancePolicy"),
    ("attendance", "AttendanceSession"),
    ("attendance", "AttendanceAlert"),
    ("attendance", "ParentNotification"),
    ("behavior", "BehaviorEvent"),
    ("activities", "Activity"),
    ("counseling", "CounselingCase"),
    ("analytics", "AnalyticsRun"),
    ("analytics", "StudentRiskSignal"),
    ("recommendations", "Recommendation"),
)


def _manager(model, alias):
    return model._base_manager.using(alias)


def _soft_delete_duplicates(model, alias, key_for):
    """Keep the oldest live row for a post-consolidation unique key."""

    manager = _manager(model, alias)
    seen = set()
    duplicate_ids = []
    for row in manager.order_by("created_at", "pk").iterator():
        if getattr(row, "is_deleted", False):
            continue
        key = key_for(row)
        if key is None:
            continue
        if key in seen:
            duplicate_ids.append(row.pk)
        else:
            seen.add(key)
    if duplicate_ids:
        manager.filter(pk__in=duplicate_ids).update(
            is_deleted=True,
            deleted_at=timezone.now(),
        )


def _rename_duplicate_class_codes(class_model, alias, school_map):
    manager = _manager(class_model, alias)
    seen = set()
    for row in manager.order_by("created_at", "pk").iterator():
        target_school_id = school_map.get(row.school_id, row.school_id)
        key = (target_school_id, row.academic_year_id, row.code)
        if key not in seen:
            seen.add(key)
            continue

        suffix = f"-legacy-{str(row.pk).replace('-', '')[:8]}"
        base = (row.code or "class")[: 30 - len(suffix)]
        candidate = f"{base}{suffix}"
        counter = 1
        while (target_school_id, row.academic_year_id, candidate) in seen:
            extra = f"-{counter}"
            candidate = f"{base[: 30 - len(suffix) - len(extra)]}{suffix}{extra}"
            counter += 1
        row.code = candidate
        row.save(update_fields=["code"])
        seen.add((target_school_id, row.academic_year_id, candidate))


def _rename_duplicate_student_numbers(enrollment_model, alias, school_map):
    manager = _manager(enrollment_model, alias).filter(
        is_deleted=False,
        status="active",
    )
    seen = set()
    for row in manager.order_by("created_at", "pk").iterator():
        target_school_id = school_map.get(row.school_id, row.school_id)
        key = (target_school_id, row.academic_year_id, row.student_number)
        if key not in seen:
            seen.add(key)
            continue

        suffix = f"-legacy-{str(row.pk).replace('-', '')[:8]}"
        row.student_number = f"{row.student_number[: 50 - len(suffix)]}{suffix}"
        row.save(update_fields=["student_number"])
        seen.add((target_school_id, row.academic_year_id, row.student_number))


def _unique_besat_code(used_codes, parent_id):
    if BESAT_CODE not in used_codes:
        code = BESAT_CODE
    else:
        parent_suffix = str(parent_id).replace("-", "")[:12]
        code = f"{BESAT_CODE}-{parent_suffix}"
        counter = 1
        while code in used_codes:
            code = f"{BESAT_CODE}-{parent_suffix}-{counter}"
            counter += 1
    used_codes.add(code)
    return code


def consolidate_legacy_schools(apps, schema_editor):
    """Convert every legacy school row into the single fixed Besat tenant.

    The canonical Organization deliberately reuses the UUID of the selected
    legacy School row.  That keeps old foreign-key values valid while the
    application tables are switched from organizations_school to
    organizations_organization in the following migrations.
    """

    alias = schema_editor.connection.alias
    organization_model = apps.get_model("organizations", "Organization")
    legacy_school_model = apps.get_model("organizations", "School")
    legacy_schools = list(
        _manager(legacy_school_model, alias).order_by("organization_id", "created_at", "pk")
    )

    by_parent = defaultdict(list)
    for school in legacy_schools:
        by_parent[school.organization_id].append(school)

    parent_ids = set(by_parent)
    parent_ids.update(
        _manager(organization_model, alias)
        .filter(organization_id__isnull=True)
        .values_list("pk", flat=True)
    )

    used_codes = set(_manager(organization_model, alias).values_list("code", flat=True))
    school_map = {}
    for parent_id in sorted(parent_ids, key=str):
        schools = by_parent.get(parent_id, [])
        if schools:
            canonical_source = next(
                (
                    school
                    for school in schools
                    if not school.is_deleted
                    and (school.code == BESAT_CODE or school.name == BESAT_NAME)
                ),
                next((school for school in schools if not school.is_deleted), schools[0]),
            )
            canonical_id = canonical_source.pk
            if _manager(organization_model, alias).filter(pk=canonical_id).exists():
                raise RuntimeError(
                    f"Cannot consolidate school {canonical_id}: an organization already uses its UUID."
                )
            logo_name = getattr(canonical_source.logo, "name", "")
        else:
            canonical_id = None
            logo_name = ""

        code = _unique_besat_code(used_codes, parent_id)
        canonical = organization_model.objects.using(alias).create(
            pk=canonical_id,
            organization_id=parent_id,
            code=code,
            name=BESAT_NAME,
            official_name=BESAT_OFFICIAL_NAME,
            phone=getattr(canonical_source, "phone", "") if schools else "",
            email=getattr(canonical_source, "email", "") if schools else "",
            address=getattr(canonical_source, "address", "") if schools else "",
            manager_name=getattr(canonical_source, "manager_name", "") if schools else "",
            logo=logo_name,
            is_active=True,
        )
        for school in schools:
            school_map[school.pk] = canonical.pk

    if not school_map:
        return

    class_model = apps.get_model("organizations", "ClassSection")
    _rename_duplicate_class_codes(class_model, alias, school_map)

    role_model = apps.get_model("accounts", "RoleAssignment")
    _soft_delete_duplicates(
        role_model,
        alias,
        lambda row: (
            row.user_id,
            school_map.get(row.school_id, row.school_id),
            row.role,
        )
        if row.school_id
        else None,
    )

    import_job_model = apps.get_model("imports", "ImportJob")
    active_import_states = {
        "uploaded",
        "analyzing",
        "preview_ready",
        "confirmed",
        "processing",
        "completed",
    }
    _soft_delete_duplicates(
        import_job_model,
        alias,
        lambda row: (
            row.organization_id,
            school_map.get(row.school_id, row.school_id),
            row.import_type,
            row.checksum,
        )
        if row.school_id and row.status in active_import_states
        else None,
    )

    manifest_model = apps.get_model("imports", "DataSourceManifest")
    _soft_delete_duplicates(
        manifest_model,
        alias,
        lambda row: (school_map.get(row.school_id, row.school_id), row.source_file)
        if row.school_id
        else None,
    )

    selection_model = apps.get_model("imports", "ClassSourceSelection")
    _soft_delete_duplicates(
        selection_model,
        alias,
        lambda row: (school_map.get(row.school_id, row.school_id), row.class_code)
        if row.school_id
        else None,
    )

    policy_model = apps.get_model("attendance", "AttendancePolicy")
    _soft_delete_duplicates(
        policy_model,
        alias,
        lambda row: (school_map.get(row.school_id, row.school_id), row.academic_year_id)
        if row.school_id
        else None,
    )

    template_model = apps.get_model("reports", "ReportTemplate")
    _soft_delete_duplicates(
        template_model,
        alias,
        lambda row: (
            row.organization_id,
            school_map.get(row.school_id, row.school_id),
            row.code,
        )
        if row.school_id
        else None,
    )

    enrollment_model = apps.get_model("students", "Enrollment")
    active_enrollments = _manager(enrollment_model, alias).filter(
        is_deleted=False,
        status="active",
    )
    seen_student_year = set()
    duplicate_active_ids = []
    for row in active_enrollments.order_by("created_at", "pk").iterator():
        key = (row.student_id, row.academic_year_id)
        if key in seen_student_year:
            duplicate_active_ids.append(row.pk)
        else:
            seen_student_year.add(key)
    if duplicate_active_ids:
        enrollment_model._base_manager.using(alias).filter(pk__in=duplicate_active_ids).update(
            status="transferred"
        )
    _rename_duplicate_student_numbers(enrollment_model, alias, school_map)

    for app_label, model_name in SCHOOL_REFERENCES:
        model = apps.get_model(app_label, model_name)
        manager = _manager(model, alias)
        for old_id, new_id in school_map.items():
            manager.filter(school_id=old_id).update(school_id=new_id)

    audit_model = apps.get_model("core", "AuditEvent")
    audit_manager = _manager(audit_model, alias)
    for old_id, new_id in school_map.items():
        audit_manager.filter(school_id=old_id).update(school_id=new_id)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_alter_roleassignment_role"),
        ("activities", "0001_initial"),
        ("analytics", "0001_initial"),
        ("attendance", "0002_notification_delivery_state"),
        ("behavior", "0001_initial"),
        ("core", "0001_initial"),
        ("counseling", "0001_initial"),
        ("imports", "0008_data_source_manifest"),
        ("organizations", "0001_initial"),
        ("recommendations", "0001_initial"),
        ("reports", "0008_reportarchive_data_monthly"),
        ("students", "0005_alter_student_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="address",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="organization",
            name="manager_name",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="organization",
            name="official_name",
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name="organization",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="children",
                to="organizations.organization",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="phone",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.RunPython(consolidate_legacy_schools, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="classsection",
            name="school",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="school_classes",
                to="organizations.organization",
            ),
        ),
    ]
