from rest_framework import serializers

from hamamooz.apps.academics.models import Assessment, CourseOffering
from hamamooz.apps.academics.services import validate_score_completeness
from hamamooz.apps.accounts.access import allowed_class_ids, selected_school_ids
from hamamooz.apps.organizations.models import Term
from hamamooz.apps.summers.models import SummerComprehensiveExam, SummerRegistration

from .models import ReportArchive, ReportDraft, ReportPeriodType, ReportTemplate
from .services import (
    ALLOWED_CONTENT_OVERRIDES,
    REPORT_CARD_LAYOUTS,
    build_draft_snapshot,
)


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
    if school.id not in set(selected_school_ids(request)):
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
    editable_download_url = serializers.SerializerMethodField()
    period_type = serializers.CharField(read_only=True)
    period_label = serializers.CharField(read_only=True)

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
            "period_type",
            "period_label",
            "report_type",
            "layout_key",
            "status",
            "status_display",
            "enrollment",
            "class_section",
            "summer_program",
            "summer_registration",
            "summer_exam",
            "requested_by",
            "requested_by_name",
            "formula_version",
            "output_format",
            "snapshot",
            "source_fingerprint",
            "tracking_code",
            "report_version",
            "download_url",
            "editable_download_url",
            "error_message",
            "started_at",
            "completed_at",
            "released_by",
            "released_at",
            "approved_by",
            "approved_at",
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
            "layout_key",
            "status",
            "status_display",
            "requested_by",
            "requested_by_name",
            "formula_version",
            "output_format",
            "snapshot",
            "source_fingerprint",
            "tracking_code",
            "report_version",
            "download_url",
            "editable_download_url",
            "error_message",
            "started_at",
            "completed_at",
            "released_by",
            "released_at",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        ]

    def get_download_url(self, obj) -> str | None:
        if obj.status != ReportArchive.Status.COMPLETED or not obj.output_file:
            return None
        request = self.context.get("request")
        path = f"/api/v1/reports/{obj.id}/download/"
        return request.build_absolute_uri(path) if request else path

    def get_editable_download_url(self, obj) -> str | None:
        if obj.status != ReportArchive.Status.COMPLETED or not obj.editable_output_file:
            return None
        request = self.context.get("request")
        path = f"/api/v1/reports/{obj.id}/download-docx/"
        return request.build_absolute_uri(path) if request else path

    def validate(self, attrs):
        if any(
            key in self.initial_data
            for key in ("layout_key", "summer_program", "summer_registration", "summer_exam")
        ):
            raise serializers.ValidationError(
                {"detail": "New official report families require a human-approved draft."}
            )
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
            "layout_key",
            "output_format",
            "blocks",
            "presentation",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        from hamamooz.apps.accounts.access import (
            accessible_organization_ids,
            administered_organization_ids,
        )

        request = self.context["request"]
        organization = attrs.get("organization") or self.instance.organization
        school = attrs.get("school", self.instance.school if self.instance else None)
        if organization.id not in set(accessible_organization_ids(request.user)):
            raise serializers.ValidationError(
                {"organization": "Organization is outside your access scope."}
            )
        is_shared_template = school is None or (
            self.instance is not None and self.instance.school_id is None
        )
        if is_shared_template and organization.id not in set(
            administered_organization_ids(request.user)
        ):
            raise serializers.ValidationError(
                {"school": "Only an organization administrator may manage shared templates."}
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
            "period_type",
            "period_label",
            "enrollment",
            "class_section",
            "summer_program",
            "summer_registration",
            "summer_exam",
            "layout_key",
            "snapshot",
            "source_fingerprint",
            "tracking_code",
            "report_version",
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
            "period_type",
            "period_label",
            "layout_key",
            "summer_program",
            "snapshot",
            "source_fingerprint",
            "tracking_code",
            "report_version",
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
        queryset=Term.objects.all(), required=False, allow_null=True
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
    summer_registration = serializers.PrimaryKeyRelatedField(
        queryset=SummerRegistration.objects.all(), required=False, allow_null=True
    )
    summer_exam = serializers.PrimaryKeyRelatedField(
        queryset=SummerComprehensiveExam.objects.all(), required=False, allow_null=True
    )

    def validate(self, attrs):
        request = self.context["request"]
        template = attrs["template"]
        enrollment = attrs.get("enrollment")
        class_section = attrs.get("class_section")
        summer_registration = attrs.get("summer_registration")
        summer_exam = attrs.get("summer_exam")
        if sum(bool(item) for item in (enrollment, class_section, summer_registration)) != 1:
            raise serializers.ValidationError(
                "Exactly one of enrollment, class_section, or summer_registration is required."
            )
        if summer_registration:
            school = summer_registration.program.school
            academic_year = summer_registration.program.academic_year
            scope_class = summer_registration.enrollment.class_section
        else:
            school = enrollment.school if enrollment else class_section.school
            academic_year = enrollment.academic_year if enrollment else class_section.academic_year
            scope_class = enrollment.class_section if enrollment else class_section
        if template.school_id and template.school_id != school.id:
            raise serializers.ValidationError(
                {"template": "Template is unavailable for this school."}
            )
        if template.organization_id != school.organization_id:
            raise serializers.ValidationError(
                {"template": "Template organization does not match the report scope."}
            )
        layout = REPORT_CARD_LAYOUTS.get(template.layout_key)
        term = attrs.get("term")
        if layout:
            if layout["period_type"] == ReportPeriodType.TERM:
                if term is None or term.code != layout["term_code"]:
                    raise serializers.ValidationError(
                        {"term": "Term must match the selected report layout."}
                    )
                if summer_registration:
                    raise serializers.ValidationError(
                        {"summer_registration": "Term reports cannot use summer registration."}
                    )
            elif layout["period_type"] == ReportPeriodType.ANNUAL:
                if term is not None or summer_registration:
                    raise serializers.ValidationError(
                        {"term": "Annual reports use an academic year, not a term."}
                    )
            else:
                if not summer_registration or enrollment or class_section or term:
                    raise serializers.ValidationError(
                        {"summer_registration": "Summer layout requires only summer registration."}
                    )
                if template.report_type != ReportArchive.ReportType.STUDENT_REPORT_CARD:
                    raise serializers.ValidationError(
                        {"template": "Summer reports are individual student reports."}
                    )
                if summer_exam and summer_exam.program_id != summer_registration.program_id:
                    raise serializers.ValidationError(
                        {"summer_exam": "Exam does not belong to the registration program."}
                    )
        elif term is None:
            raise serializers.ValidationError({"term": "Legacy reports require a term."})
        if term and term.academic_year_id != academic_year.id:
            raise serializers.ValidationError({"term": "Term does not belong to the report year."})
        if school.id not in set(selected_school_ids(request)):
            raise serializers.ValidationError({"detail": "School is outside your access scope."})
        if scope_class.id not in set(allowed_class_ids(request.user, [school.id])):
            raise serializers.ValidationError({"detail": "Class is outside your access scope."})
        if (
            template.report_type == ReportArchive.ReportType.STUDENT_REPORT_CARD
            and not enrollment
            and not summer_registration
        ):
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
        attrs["_summer_program"] = (
            summer_registration.program if summer_registration is not None else None
        )
        return attrs

    def create(self, validated_data):
        school = validated_data.pop("_school")
        academic_year = validated_data.pop("_academic_year")
        summer_program = validated_data.pop("_summer_program")
        template = validated_data["template"]
        snapshot = build_draft_snapshot(
            template,
            term=validated_data.get("term"),
            enrollment=validated_data.get("enrollment"),
            class_section=validated_data.get("class_section"),
            summer_registration=validated_data.get("summer_registration"),
            summer_exam=validated_data.get("summer_exam"),
        )
        draft = ReportDraft(
            **validated_data,
            organization=school.organization,
            school=school,
            academic_year=academic_year,
            layout_key=template.layout_key,
            summer_program=summer_program,
            snapshot=snapshot,
            source_fingerprint=snapshot.get("source_fingerprint", ""),
            created_by=self.context["request"].user,
        )
        draft.full_clean(exclude=["id"])
        draft.save()
        return draft


class ReportDraftContentSerializer(serializers.Serializer):
    content_overrides = serializers.JSONField()

    def validate_content_overrides(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Content overrides must be an object.")
        invalid = set(value) - set(ALLOWED_CONTENT_OVERRIDES)
        if invalid:
            raise serializers.ValidationError(
                f"Only harmless presentation text may be overridden: {', '.join(sorted(invalid))}."
            )
        if any(not isinstance(item, str) for item in value.values()):
            raise serializers.ValidationError("Each override must be plain text.")
        oversized = [
            key for key, text in value.items() if len(text) > ALLOWED_CONTENT_OVERRIDES[key]
        ]
        if oversized:
            raise serializers.ValidationError(
                f"Presentation text is too long: {', '.join(sorted(oversized))}."
            )
        return value


class ReportDraftTransitionSerializer(serializers.Serializer):
    target_status = serializers.ChoiceField(
        choices=[choice for choice, _ in ReportDraft.Status.choices]
    )
    rejection_reason = serializers.CharField(required=False, allow_blank=False, max_length=500)
