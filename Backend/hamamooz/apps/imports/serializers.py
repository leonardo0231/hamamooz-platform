import hashlib
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework import serializers

from hamamooz.apps.accounts.access import accessible_school_ids
from hamamooz.apps.organizations.models import School

from .defaults import get_default_school
from .models import DataPathImport, ImportJob


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
            "source_kind",
            "data_path_import",
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
            "source_kind",
            "data_path_import",
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


class DataPathImportSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    school_name = serializers.CharField(source="school.name", read_only=True)

    class Meta:
        model = DataPathImport
        fields = [
            "id",
            "organization",
            "organization_name",
            "school",
            "school_name",
            "source_root",
            "status",
            "status_display",
            "overwrite_photos",
            "generate_reports",
            "report_month",
            "manifest",
            "result_summary",
            "errors",
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
            "manifest",
            "result_summary",
            "errors",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]


class DataPathImportCreateSerializer(serializers.Serializer):
    school = serializers.PrimaryKeyRelatedField(queryset=School.objects.all())
    source_root = serializers.CharField(required=False, allow_blank=True)
    overwrite_photos = serializers.BooleanField(required=False, default=False)
    generate_reports = serializers.BooleanField(required=False, default=True)
    report_month = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=12)

    def validate(self, attrs):
        request = self.context["request"]
        school = attrs["school"]
        if school.id not in set(accessible_school_ids(request.user)):
            raise serializers.ValidationError({"school": "به این شعبه دسترسی ندارید."})
        source_root = Path(attrs.get("source_root") or settings.DATA_ROOT).expanduser().resolve()
        configured_root = Path(settings.DATA_ROOT).resolve()
        if source_root != configured_root:
            raise serializers.ValidationError(
                {"source_root": "برای امنیت، API فقط مسیر Data پیکربندی‌شدهٔ سرور را می‌خواند."}
            )
        if not source_root.is_dir():
            raise serializers.ValidationError({"source_root": "مسیر Data روی سرور پیدا نشد."})
        attrs["source_root"] = str(source_root)
        return attrs

    def create(self, validated_data):
        school = validated_data["school"]
        return DataPathImport.objects.create(
            organization=school.organization,
            requested_by=self.context["request"].user,
            **validated_data,
        )
