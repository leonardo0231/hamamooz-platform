import hashlib
from pathlib import Path

from django.db import IntegrityError, transaction
from rest_framework import serializers

from hamamooz.apps.accounts.access import accessible_school_ids
from hamamooz.apps.organizations.models import Organization

from .defaults import get_besat_organization
from .models import (
    ClassSourceSelection,
    DataSourceConflict,
    DataSourceManifest,
    ImportJob,
    SubjectExamResult,
)


def uploaded_file_checksum(uploaded_file):
    digest = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest()


class ImportJobSerializer(serializers.ModelSerializer):
    # The database keeps this relation for historical provenance, but the API
    # never accepts a client-selected school.  Every import is assigned to the
    # configured Besat organization in ``validate``.
    school = serializers.PrimaryKeyRelatedField(read_only=True)
    requested_by_name = serializers.CharField(source="requested_by.get_full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    school_name = serializers.CharField(source="school.name", read_only=True)

    class Meta:
        model = ImportJob
        fields = [
            "id",
            "organization",
            "organization_name",
            "school",
            "school_name",
            "import_type",
            "status",
            "status_display",
            "source_file",
            "checksum",
            "requested_by",
            "requested_by_name",
            "total_rows",
            "successful_rows",
            "error_count",
            "errors",
            "result_summary",
            "preview_summary",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "organization_name",
            "school_name",
            "status",
            "status_display",
            "checksum",
            "requested_by",
            "requested_by_name",
            "total_rows",
            "successful_rows",
            "error_count",
            "errors",
            "result_summary",
            "preview_summary",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        try:
            school = get_besat_organization(organization_ids=accessible_school_ids(request.user))
        except Organization.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"school": "مدرسه بعثت برای ثبت فایل پیکربندی نشده است."}
            ) from exc
        attrs["_school"] = school

        source = attrs.get("source_file")
        import_type = attrs.get("import_type")

        if import_type != ImportJob.ImportType.COMPREHENSIVE_SCHOOL:
            raise serializers.ValidationError({"import_type": "فقط فایل جامع مدرسه مجاز است."})

        if Path(source.name).suffix.lower() != ".xlsx":
            raise serializers.ValidationError({"source_file": "فقط فایل XLSX پذیرفته می‌شود."})

        if source.size > 10 * 1024 * 1024:
            raise serializers.ValidationError({"source_file": "حجم فایل بیشتر از ۱۰ مگابایت است."})

        checksum = uploaded_file_checksum(source)
        attrs["_checksum"] = checksum

        duplicate_states = [
            ImportJob.Status.UPLOADED,
            ImportJob.Status.ANALYZING,
            ImportJob.Status.PREVIEW_READY,
            ImportJob.Status.CONFIRMED,
            ImportJob.Status.PROCESSING,
            ImportJob.Status.COMPLETED,
        ]

        if ImportJob.objects.filter(
            organization=school.organization,
            school=school,
            import_type=import_type,
            checksum=checksum,
            status__in=duplicate_states,
        ).exists():
            raise serializers.ValidationError("این فایل قبلاً ثبت یا پردازش شده است.")

        return attrs

    def create(self, validated_data):
        checksum = validated_data.pop("_checksum")
        school = validated_data.pop("_school")

        try:
            with transaction.atomic():
                return ImportJob.objects.create(
                    organization=school.organization,
                    school=school,
                    requested_by=self.context["request"].user,
                    checksum=checksum,
                    **validated_data,
                )
        except IntegrityError as exc:
            raise serializers.ValidationError("این فایل قبلاً ثبت شده است.") from exc


class ImportJobCreateSerializer(ImportJobSerializer):
    import_type = serializers.ChoiceField(
        choices=[(ImportJob.ImportType.COMPREHENSIVE_SCHOOL, "فایل جامع مدرسه")]
    )


class DataSourceManifestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = DataSourceManifest
        fields = [
            "id",
            "organization",
            "school",
            "source_file",
            "checksum",
            "file_size",
            "status",
            "status_display",
            "detected_classes",
            "sheet_manifest",
            "errors",
            "row_count",
            "student_row_count",
            "scanned_at",
            "ingest_status",
            "ingest_summary",
            "ingested_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SubjectExamResultSerializer(serializers.ModelSerializer):
    """Read-only audit representation of a standalone subject-exam row."""

    school_name = serializers.CharField(source="school.name", read_only=True)
    student_name = serializers.CharField(
        source="student.full_name", read_only=True, allow_null=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SubjectExamResult
        fields = [
            "id",
            "organization",
            "school",
            "school_name",
            "source_manifest",
            "source_file",
            "source_checksum",
            "source_sheet",
            "source_row",
            "exam_period",
            "first_name",
            "last_name",
            "national_id_raw",
            "national_id",
            "grade_name",
            "grade_order",
            "class_name",
            "subject_name",
            "student",
            "student_name",
            "question_count",
            "correct_count",
            "wrong_count",
            "blank_count",
            "percentage",
            "highest_percentage",
            "rank",
            "t_score",
            "overall_rank",
            "score",
            "final_score",
            "raw_values",
            "normalized_values",
            "errors",
            "error_count",
            "status",
            "status_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DataSourceConflictSerializer(serializers.ModelSerializer):
    conflict_type_display = serializers.CharField(
        source="get_conflict_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    manifests = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = DataSourceConflict
        fields = [
            "id",
            "school",
            "conflict_type",
            "conflict_type_display",
            "status",
            "status_display",
            "class_code",
            "national_id",
            "manifests",
            "details",
            "resolution_note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ClassSourceSelectionSerializer(serializers.ModelSerializer):
    school = serializers.PrimaryKeyRelatedField(read_only=True)
    selected_by_name = serializers.CharField(source="selected_by.get_full_name", read_only=True)

    class Meta:
        model = ClassSourceSelection
        fields = [
            "id",
            "school",
            "class_code",
            "manifest",
            "selected_by",
            "selected_by_name",
            "selection_note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "selected_by", "selected_by_name", "created_at", "updated_at"]

    def validate(self, attrs):
        manifest = attrs.get("manifest")
        if manifest is None and self.instance is not None:
            manifest = self.instance.manifest
        school = manifest.school if manifest is not None else getattr(self.instance, "school", None)
        class_code = str(
            attrs.get("class_code") or getattr(self.instance, "class_code", "")
        ).strip()
        if not school or not manifest:
            raise serializers.ValidationError("مدرسه و فایل منبع اصلی الزامی هستند.")
        if manifest.school_id != school.id:
            raise serializers.ValidationError(
                {"manifest": "فایل منبع متعلق به مدرسه انتخابی نیست."}
            )
        if manifest.status in {
            DataSourceManifest.Status.INVALID,
            DataSourceManifest.Status.INCOMPLETE,
        }:
            raise serializers.ValidationError(
                {"manifest": "فایل ناقص یا نامعتبر قابل انتخاب نیست."}
            )
        if class_code not in manifest.detected_classes:
            raise serializers.ValidationError(
                {"class_code": "این کلاس در فایل منبع انتخابی پیدا نشد."}
            )
        if self.instance is None:
            attrs["_school"] = school
        return attrs

    def create(self, validated_data):
        school = validated_data.pop("_school")
        return ClassSourceSelection.objects.create(school=school, **validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("_school", None)
        return super().update(instance, validated_data)
