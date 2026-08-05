from rest_framework import serializers

from hamamooz.apps.academics.models import Assessment, CourseOffering
from hamamooz.apps.academics.services import validate_score_completeness
from hamamooz.apps.accounts.access import accessible_school_ids, allowed_class_ids

from .models import ReportArchive


def validate_report_selection(attrs, request):
    report_type = attrs["report_type"]
    enrollment = attrs.get("enrollment")
    class_section = attrs.get("class_section")
    term = attrs["term"]
    if report_type == ReportArchive.ReportType.STUDENT_REPORT_CARD:
        if not enrollment or class_section:
            raise serializers.ValidationError(
                "برای کارنامه دانش‌آموز فقط enrollment باید ارسال شود."
            )
        school = enrollment.school
        class_section = enrollment.class_section
        academic_year = enrollment.academic_year
    else:
        if not class_section or enrollment:
            raise serializers.ValidationError(
                "برای کارنامه گروهی فقط class_section باید ارسال شود."
            )
        school = class_section.school
        academic_year = class_section.academic_year
    if term.academic_year_id != academic_year.id:
        raise serializers.ValidationError({"term": "نوبت متعلق به سال تحصیلی انتخاب‌شده نیست."})
    if school.id not in set(accessible_school_ids(request.user)):
        raise serializers.ValidationError("به این شعبه دسترسی ندارید.")
    if class_section.id not in set(allowed_class_ids(request.user, [school.id])):
        raise serializers.ValidationError("به این کلاس دسترسی ندارید.")
    attrs["_school"] = school
    attrs["_academic_year"] = academic_year
    return attrs


def validate_official_report_readiness(attrs):
    """Only create an immutable official archive after every course is fully locked."""
    term = attrs["term"]
    class_section = attrs.get("class_section") or attrs["enrollment"].class_section
    offerings = CourseOffering.objects.filter(
        class_section=class_section,
        term=term,
        is_active=True,
    ).select_related("grade_subject__subject")
    if not offerings.exists():
        raise serializers.ValidationError("برای این کلاس و نوبت هیچ درس فعالی تعریف نشده است.")

    should_validate_roster = (
        attrs["report_type"] == ReportArchive.ReportType.CLASS_REPORT_CARDS
        or attrs["enrollment"].status == "active"
    )
    incomplete = []
    for offering in offerings:
        assessments = list(offering.assessments.all())
        is_incomplete = not assessments or any(
            assessment.status != Assessment.Status.LOCKED for assessment in assessments
        )
        if not is_incomplete and should_validate_roster:
            try:
                for assessment in assessments:
                    validate_score_completeness(assessment)
            except serializers.ValidationError:
                is_incomplete = True
        if is_incomplete:
            incomplete.append(offering.grade_subject.subject.title)
    if incomplete:
        titles = "، ".join(incomplete[:10])
        raise serializers.ValidationError(
            {"detail": f"برای صدور رسمی، همه ارزیابی‌های دروس باید قفل شوند: {titles}"}
        )
    return attrs


class ReportArchiveSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.get_full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    school_name = serializers.CharField(source="school.name", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ReportArchive
        fields = [
            "id",
            "organization",
            "organization_name",
            "school",
            "school_name",
            "academic_year",
            "term",
            "report_type",
            "status",
            "status_display",
            "enrollment",
            "class_section",
            "requested_by",
            "requested_by_name",
            "formula_version",
            "snapshot",
            "download_url",
            "error_message",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "organization_name",
            "school",
            "school_name",
            "academic_year",
            "status",
            "status_display",
            "requested_by",
            "requested_by_name",
            "formula_version",
            "snapshot",
            "download_url",
            "error_message",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def get_download_url(self, obj) -> str | None:
        if obj.status != ReportArchive.Status.COMPLETED or not obj.output_file:
            return None
        request = self.context.get("request")
        path = f"/api/v1/reports/{obj.id}/download/"
        return request.build_absolute_uri(path) if request else path

    def validate(self, attrs):
        attrs = validate_report_selection(attrs, self.context["request"])
        return validate_official_report_readiness(attrs)

    def create(self, validated_data):
        school = validated_data.pop("_school")
        academic_year = validated_data.pop("_academic_year")
        return ReportArchive.objects.create(
            organization=school.organization,
            school=school,
            academic_year=academic_year,
            requested_by=self.context["request"].user,
            **validated_data,
        )


class ReportPreviewSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=ReportArchive.ReportType.choices)
    term = serializers.PrimaryKeyRelatedField(
        queryset=ReportArchive._meta.get_field("term").remote_field.model.objects.all()
    )
    enrollment = serializers.PrimaryKeyRelatedField(
        queryset=ReportArchive._meta.get_field("enrollment").remote_field.model.objects.all(),
        required=False,
        allow_null=True,
    )
    class_section = serializers.PrimaryKeyRelatedField(
        queryset=ReportArchive._meta.get_field("class_section").remote_field.model.objects.all(),
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        return validate_report_selection(attrs, self.context["request"])
