import hashlib
from pathlib import Path

from django.db import IntegrityError, transaction
from rest_framework import serializers

from hamamooz.apps.accounts.access import accessible_school_ids

from .models import ImportJob


def uploaded_file_checksum(uploaded_file):
    digest = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest()


class ImportJobSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.get_full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ImportJob
        fields = [
            "id",
            "organization",
            "school",
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
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "status",
            "status_display",
            "checksum",
            "requested_by",
            "requested_by_name",
            "total_rows",
            "successful_rows",
            "error_count",
            "errors",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        source = attrs.get("source_file")
        school = attrs.get("school")
        request = self.context["request"]
        if school.id not in set(accessible_school_ids(request.user)):
            raise serializers.ValidationError({"school": "به این شعبه دسترسی ندارید."})
        extension = Path(source.name).suffix.lower()
        if extension not in {".xlsx", ".xls"}:
            raise serializers.ValidationError(
                {"source_file": "فقط فایل‌های XLSX و XLS پذیرفته می‌شوند."}
            )
        if source.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                {"source_file": "حجم فایل نباید بیشتر از ۱۰ مگابایت باشد."}
            )
        checksum = uploaded_file_checksum(source)
        attrs["_checksum"] = checksum
        duplicate = ImportJob.objects.filter(
            organization=school.organization,
            school=school,
            import_type=attrs["import_type"],
            checksum=checksum,
            status__in=[
                ImportJob.Status.QUEUED,
                ImportJob.Status.PROCESSING,
                ImportJob.Status.COMPLETED,
            ],
        ).exists()
        if duplicate:
            raise serializers.ValidationError(
                "این فایل قبلاً برای همین شعبه و نوع Import ثبت شده است."
            )
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
            raise serializers.ValidationError(
                "این فایل قبلاً برای همین شعبه و نوع Import ثبت شده است."
            ) from exc
