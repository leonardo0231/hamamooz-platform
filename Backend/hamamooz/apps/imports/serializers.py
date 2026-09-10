import hashlib
from pathlib import Path

from django.db import IntegrityError, transaction
from rest_framework import serializers

from hamamooz.apps.accounts.access import accessible_school_ids
from hamamooz.apps.organizations.models import School

from .defaults import get_default_school
from .models import ClassSourceSelection, DataSourceConflict, DataSourceManifest, ImportJob


def uploaded_file_checksum(uploaded_file):
    digest = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest()


class ImportJobSerializer(serializers.ModelSerializer):
    school = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.all(), required=False, allow_null=True
    )
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
        school = attrs.get("school")
        if school is None:
            try:
                school = get_default_school(school_ids=accessible_school_ids(request.user))
            except School.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"school": "هیچ شعبهٔ فعالی برای ثبت فایل در دسترس نیست."}
                ) from exc
            attrs["school"] = school

        source = attrs.get("source_file")
        import_type = attrs.get("import_type")

        if school.id not in set(accessible_school_ids(request.user)):
            raise serializers.ValidationError({"school": "به این شعبه دسترسی ندارید."})

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
        school = validated_data["school"]

        try:
            with transaction.atomic():
                return ImportJob.objects.create(
                    organization=school.organization,
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
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DataSourceConflictSerializer(serializers.ModelSerializer):
    conflict_type_display = serializers.CharField(source="get_conflict_type_display", read_only=True)
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
        school = attrs.get("school") or getattr(self.instance, "school", None)
        manifest = attrs.get("manifest")
        if manifest is None and self.instance is not None:
            manifest = self.instance.manifest
        class_code = str(attrs.get("class_code") or getattr(self.instance, "class_code", "")).strip()
        if not school or not manifest:
            raise serializers.ValidationError("مدرسه و فایل منبع اصلی الزامی هستند.")
        if manifest.school_id != school.id:
            raise serializers.ValidationError({"manifest": "فایل منبع متعلق به مدرسه انتخابی نیست."})
        if manifest.status in {
            DataSourceManifest.Status.INVALID,
            DataSourceManifest.Status.INCOMPLETE,
        }:
            raise serializers.ValidationError({"manifest": "فایل ناقص یا نامعتبر قابل انتخاب نیست."})
        if class_code not in manifest.detected_classes:
            raise serializers.ValidationError(
                {"class_code": "این کلاس در فایل منبع انتخابی پیدا نشد."}
            )
        return attrs
