from rest_framework import serializers

from hamamooz.apps.academics.models import Assessment, CourseOffering
from hamamooz.apps.academics.services import validate_score_completeness
from hamamooz.apps.accounts.access import accessible_school_ids, allowed_class_ids

from .models import ReportArchive, ReportBatch, ReportBatchItem, ReportDraft, ReportTemplate
from .services import ALLOWED_REPORT_BLOCKS, build_draft_snapshot


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
            "output_format",
            "snapshot",
            "download_url",
            "error_message",
            "started_at",
            "completed_at",
            "released_by",
            "released_at",
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
            "output_format",
            "snapshot",
            "download_url",
            "error_message",
            "started_at",
            "completed_at",
            "released_by",
            "released_at",
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


class ReportBatchItemSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)
    national_id = serializers.CharField(source="enrollment.student.national_id", read_only=True)
    report_id = serializers.UUIDField(source="report.id", read_only=True, allow_null=True)

    class Meta:
        model = ReportBatchItem
        fields = ["id", "student_name", "national_id", "enrollment", "report_id", "status", "error_message"]


class ReportBatchSerializer(serializers.ModelSerializer):
    progress_percent = serializers.IntegerField(read_only=True)
    zip_download_url = serializers.SerializerMethodField()
    items = ReportBatchItemSerializer(many=True, read_only=True)

    class Meta:
        model = ReportBatch
        fields = [
            "id", "organization", "school", "academic_year", "term", "class_section", "scope", "page_size",
            "status", "total_count", "completed_count", "failed_count", "progress_percent", "zip_download_url",
            "started_at", "completed_at", "error_message", "requested_by", "created_at", "items",
        ]
        read_only_fields = fields

    def get_zip_download_url(self, obj):
        if not obj.zip_file or obj.status not in [ReportBatch.Status.COMPLETED, ReportBatch.Status.PARTIAL]:
            return None
        request = self.context.get("request")
        path = f"/api/v1/reports/batches/{obj.id}/download/"
        return request.build_absolute_uri(path) if request else path


class ReportBatchCreateSerializer(serializers.Serializer):
    school = serializers.PrimaryKeyRelatedField(queryset=ReportArchive._meta.get_field("school").remote_field.model.objects.all())
    academic_year = serializers.PrimaryKeyRelatedField(queryset=ReportArchive._meta.get_field("academic_year").remote_field.model.objects.all())
    term = serializers.PrimaryKeyRelatedField(queryset=ReportArchive._meta.get_field("term").remote_field.model.objects.all())
    scope = serializers.ChoiceField(choices=ReportBatch.Scope.choices)
    class_section = serializers.PrimaryKeyRelatedField(queryset=ReportArchive._meta.get_field("class_section").remote_field.model.objects.all(), required=False, allow_null=True)
    page_size = serializers.ChoiceField(choices=[("a3_landscape", "A3 landscape"), ("a4_portrait", "A4 portrait")], default="a3_landscape")

    def validate(self, attrs):
        request, school, year, term = self.context["request"], attrs["school"], attrs["academic_year"], attrs["term"]
        if school.id not in set(accessible_school_ids(request.user)):
            raise serializers.ValidationError({"school": "School is outside your access scope."})
        if year.organization_id != school.organization_id or term.academic_year_id != year.id:
            raise serializers.ValidationError({"term": "Term must belong to the selected academic year."})
        section = attrs.get("class_section")
        if attrs["scope"] == ReportBatch.Scope.CLASS:
            if not section or section.school_id != school.id or section.academic_year_id != year.id:
                raise serializers.ValidationError({"class_section": "A class in the selected school and year is required."})
            target_classes = [section.id]
        else:
            if section:
                raise serializers.ValidationError({"class_section": "School scope does not accept a class."})
            target_classes = list(school.classes.filter(academic_year=year).values_list("id", flat=True))
        allowed = set(allowed_class_ids(request.user, [school.id]))
        if not set(target_classes).issubset(allowed):
            raise serializers.ValidationError({"detail": "One or more classes are outside your access scope."})
        # A group is official only when every selected class has locked, complete scores.
        for selected_class in ReportArchive._meta.get_field("class_section").remote_field.model.objects.filter(id__in=target_classes):
            validate_official_report_readiness(
                {"report_type": ReportArchive.ReportType.CLASS_REPORT_CARDS, "term": term, "class_section": selected_class}
            )
        attrs["_target_classes"] = target_classes
        return attrs

    def create(self, validated_data):
        target_classes = validated_data.pop("_target_classes")
        school = validated_data["school"]
        batch = ReportBatch.objects.create(organization=school.organization, requested_by=self.context["request"].user, **validated_data)
        from hamamooz.apps.students.models import Enrollment
        enrollments = Enrollment.objects.filter(class_section_id__in=target_classes, status=Enrollment.Status.ACTIVE).select_related("student")
        ReportBatchItem.objects.bulk_create([ReportBatchItem(batch=batch, enrollment=item) for item in enrollments])
        batch.total_count = len(enrollments)
        batch.save(update_fields=["total_count", "updated_at"])
        return batch


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


class ReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTemplate
        fields = [
            "id",
            "organization",
            "school",
            "code",
            "title",
            "report_type",
            "output_format",
            "blocks",
            "presentation",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        from hamamooz.apps.accounts.access import accessible_organization_ids, selected_school_ids

        request = self.context["request"]
        organization = attrs.get("organization") or self.instance.organization
        school = attrs.get("school", self.instance.school if self.instance else None)
        if organization.id not in set(accessible_organization_ids(request.user)):
            raise serializers.ValidationError(
                {"organization": "Organization is outside your access scope."}
            )
        if school and school.id not in set(selected_school_ids(request)):
            raise serializers.ValidationError(
                {"school": "School is outside the selected access scope."}
            )
        instance = self.instance or ReportTemplate()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean(exclude=["id"])
        return attrs


class ReportDraftSerializer(serializers.ModelSerializer):
    archive_id = serializers.UUIDField(source="archive.id", read_only=True, allow_null=True)

    class Meta:
        model = ReportDraft
        fields = [
            "id",
            "template",
            "organization",
            "school",
            "academic_year",
            "term",
            "enrollment",
            "class_section",
            "snapshot",
            "content_overrides",
            "status",
            "created_by",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "archive_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "school",
            "academic_year",
            "snapshot",
            "status",
            "created_by",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "archive_id",
            "created_at",
            "updated_at",
        ]


class ReportDraftCreateSerializer(serializers.Serializer):
    template = serializers.PrimaryKeyRelatedField(
        queryset=ReportTemplate.objects.filter(is_active=True)
    )
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
        request = self.context["request"]
        template = attrs["template"]
        enrollment = attrs.get("enrollment")
        class_section = attrs.get("class_section")
        if bool(enrollment) == bool(class_section):
            raise serializers.ValidationError(
                "Exactly one of enrollment or class_section is required."
            )
        school = enrollment.school if enrollment else class_section.school
        academic_year = enrollment.academic_year if enrollment else class_section.academic_year
        if template.school_id and template.school_id != school.id:
            raise serializers.ValidationError(
                {"template": "Template is unavailable for this school."}
            )
        if template.organization_id != school.organization_id:
            raise serializers.ValidationError(
                {"template": "Template organization does not match the report scope."}
            )
        if attrs["term"].academic_year_id != academic_year.id:
            raise serializers.ValidationError(
                {"term": "Term does not belong to the report academic year."}
            )
        if school.id not in set(accessible_school_ids(request.user)):
            raise serializers.ValidationError({"detail": "School is outside your access scope."})
        scope_class = enrollment.class_section if enrollment else class_section
        if scope_class.id not in set(allowed_class_ids(request.user, [school.id])):
            raise serializers.ValidationError({"detail": "Class is outside your access scope."})
        if template.report_type == ReportArchive.ReportType.STUDENT_REPORT_CARD and not enrollment:
            raise serializers.ValidationError(
                {"enrollment": "Student templates require enrollment."}
            )
        if (
            template.report_type == ReportArchive.ReportType.CLASS_REPORT_CARDS
            and not class_section
        ):
            raise serializers.ValidationError(
                {"class_section": "Class templates require class_section."}
            )
        attrs["_school"] = school
        attrs["_academic_year"] = academic_year
        return attrs

    def create(self, validated_data):
        school = validated_data.pop("_school")
        academic_year = validated_data.pop("_academic_year")
        template = validated_data["template"]
        snapshot = build_draft_snapshot(
            template,
            term=validated_data["term"],
            enrollment=validated_data.get("enrollment"),
            class_section=validated_data.get("class_section"),
        )
        return ReportDraft.objects.create(
            **validated_data,
            organization=school.organization,
            school=school,
            academic_year=academic_year,
            snapshot=snapshot,
            created_by=self.context["request"].user,
        )


class ReportDraftContentSerializer(serializers.Serializer):
    content_overrides = serializers.JSONField()

    def validate_content_overrides(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Content overrides must be an object.")
        invalid = set(value) - ALLOWED_REPORT_BLOCKS
        if invalid:
            raise serializers.ValidationError(
                f"Only allowlisted blocks may be overridden: {', '.join(sorted(invalid))}."
            )
        if any(not isinstance(item, str) for item in value.values()):
            raise serializers.ValidationError("Each override must be plain text.")
        return value


class ReportDraftTransitionSerializer(serializers.Serializer):
    target_status = serializers.ChoiceField(
        choices=[choice for choice, _ in ReportDraft.Status.choices]
    )
    rejection_reason = serializers.CharField(required=False, allow_blank=False, max_length=500)
