from contextlib import suppress

from rest_framework import serializers

from hamamooz.apps.academics.models import Assessment, CourseOffering
from hamamooz.apps.academics.services import validate_score_completeness
from hamamooz.apps.accounts.access import accessible_school_ids, allowed_class_ids
from hamamooz.apps.organizations.models import Organization
from hamamooz.apps.organizations.services import get_besat_organization

from .models import ReportArchive, ReportBatch, ReportBatchItem, ReportDraft, ReportTemplate
from .services import (
    ALLOWED_REPORT_BLOCKS,
    REPORT_PAGE_SIZE_KEY,
    build_draft_snapshot,
    normalize_report_page_size,
)

MONTH_TITLES = {
    # Data workbooks use a school-period sequence that starts in summer, not
    # the Jalali calendar number: 3 is therefore شهریور by contract.
    1: "تیر",
    2: "مرداد",
    3: "شهریور",
    4: "مهر",
    5: "آبان",
    6: "آذر",
    7: "دی",
    8: "بهمن",
    9: "اسفند",
    10: "فروردین",
    11: "اردیبهشت",
    12: "خرداد",
}


def validate_report_selection(attrs, request):
    report_type = attrs["report_type"]
    enrollment = attrs.get("enrollment")
    class_section = attrs.get("class_section")
    report_mode = attrs.get("report_mode", ReportArchive.ReportMode.OFFICIAL_TERM)
    term = attrs.get("term")
    if report_mode == ReportArchive.ReportMode.DATA_MONTHLY:
        if report_type != ReportArchive.ReportType.STUDENT_REPORT_CARD:
            raise serializers.ValidationError(
                {"report_type": "گزارش ماهانه فقط برای یک دانش‌آموز صادر می‌شود."}
            )
        if not enrollment or class_section:
            raise serializers.ValidationError("برای گزارش ماهانه فقط enrollment باید ارسال شود.")
        if term is not None:
            raise serializers.ValidationError({"term": "گزارش ماهانه نوبت رسمی ندارد."})
        if not attrs.get("month_no"):
            raise serializers.ValidationError(
                {"month_no": "شماره ماه برای گزارش ماهانه الزامی است."}
            )
        school = enrollment.school
        class_section = enrollment.class_section
        academic_year = enrollment.academic_year
    elif report_mode == ReportArchive.ReportMode.OFFICIAL_TERM:
        if term is None:
            raise serializers.ValidationError({"term": "نوبت برای کارنامه رسمی الزامی است."})
        if attrs.get("month_no") is not None or attrs.get("month_title"):
            raise serializers.ValidationError(
                {"month_no": "شماره و عنوان ماه فقط برای گزارش ماهانه مجاز است."}
            )
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
    else:
        raise serializers.ValidationError({"report_mode": "حالت گزارش نامعتبر است."})
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
            "report_mode",
            "month_no",
            "month_title",
            "source_file",
            "source_row",
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
        report_mode = attrs.get("report_mode", ReportArchive.ReportMode.OFFICIAL_TERM)
        if report_mode == ReportArchive.ReportMode.DATA_MONTHLY:
            month_no = attrs.get("month_no")
            if month_no and not attrs.get("month_title"):
                attrs["month_title"] = MONTH_TITLES[month_no]
            if not str(attrs.get("source_file") or "").strip():
                raise serializers.ValidationError(
                    {"source_file": "فایل منبع برای گزارش ماهانه الزامی است."}
                )
            if attrs.get("source_row") is None:
                raise serializers.ValidationError(
                    {"source_row": "ردیف منبع برای گزارش ماهانه الزامی است."}
                )
        attrs = validate_report_selection(attrs, self.context["request"])
        return (
            validate_official_report_readiness(attrs)
            if report_mode == ReportArchive.ReportMode.OFFICIAL_TERM
            else attrs
        )

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
        fields = [
            "id",
            "student_name",
            "national_id",
            "enrollment",
            "report_id",
            "status",
            "error_message",
        ]


class ReportBatchSerializer(serializers.ModelSerializer):
    progress_percent = serializers.IntegerField(read_only=True)
    zip_download_url = serializers.SerializerMethodField()
    items = ReportBatchItemSerializer(many=True, read_only=True)

    class Meta:
        model = ReportBatch
        fields = [
            "id",
            "organization",
            "school",
            "academic_year",
            "term",
            "class_section",
            "scope",
            "page_size",
            "status",
            "total_count",
            "completed_count",
            "failed_count",
            "progress_percent",
            "zip_download_url",
            "started_at",
            "completed_at",
            "error_message",
            "requested_by",
            "created_at",
            "items",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Existing rows may predate the fixed print profile.  Never expose a
        # selectable/ambiguous page size to a report-card consumer.
        data["page_size"] = REPORT_PAGE_SIZE_KEY
        return data

    def get_zip_download_url(self, obj) -> str | None:
        if not obj.zip_file or obj.status not in [
            ReportBatch.Status.COMPLETED,
            ReportBatch.Status.PARTIAL,
        ]:
            return None
        request = self.context.get("request")
        path = f"/api/v1/reports/batches/{obj.id}/download/"
        return request.build_absolute_uri(path) if request else path


class ReportBatchCreateSerializer(serializers.Serializer):
    academic_year = serializers.PrimaryKeyRelatedField(
        queryset=ReportArchive._meta.get_field("academic_year").remote_field.model.objects.all()
    )
    term = serializers.PrimaryKeyRelatedField(
        queryset=ReportArchive._meta.get_field("term").remote_field.model.objects.all()
    )
    scope = serializers.ChoiceField(choices=ReportBatch.Scope.choices)
    class_section = serializers.PrimaryKeyRelatedField(
        queryset=ReportArchive._meta.get_field("class_section").remote_field.model.objects.all(),
        required=False,
        allow_null=True,
    )
    # Accept known legacy values for old clients, then normalize them in
    # ``validate_page_size`` so every newly queued batch is A3 landscape.
    page_size = serializers.CharField(required=False, default=REPORT_PAGE_SIZE_KEY)

    def validate_page_size(self, value):
        try:
            return normalize_report_page_size(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        request, year, term = (
            self.context["request"],
            attrs["academic_year"],
            attrs["term"],
        )
        try:
            school = get_besat_organization(
                organization_ids=accessible_school_ids(request.user),
            )
        except Organization.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"detail": "مدرسه بعثت برای تولید گزارش پیکربندی نشده است."}
            ) from exc
        attrs["school"] = school
        if year.organization_id != school.organization_id or term.academic_year_id != year.id:
            raise serializers.ValidationError(
                {"term": "Term must belong to the selected academic year."}
            )
        section = attrs.get("class_section")
        if attrs["scope"] == ReportBatch.Scope.CLASS:
            if not section or section.school_id != school.id or section.academic_year_id != year.id:
                raise serializers.ValidationError(
                    {"class_section": "A class in the selected school and year is required."}
                )
            target_classes = [section.id]
        else:
            if section:
                raise serializers.ValidationError(
                    {"class_section": "School scope does not accept a class."}
                )
            target_classes = list(
                school.school_classes.filter(academic_year=year).values_list("id", flat=True)
            )
        allowed = set(allowed_class_ids(request.user, [school.id]))
        if not set(target_classes).issubset(allowed):
            raise serializers.ValidationError(
                {"detail": "One or more classes are outside your access scope."}
            )
        # A group is official only when every selected class has locked, complete scores.
        for selected_class in ReportArchive._meta.get_field(
            "class_section"
        ).remote_field.model.objects.filter(id__in=target_classes):
            validate_official_report_readiness(
                {
                    "report_type": ReportArchive.ReportType.CLASS_REPORT_CARDS,
                    "term": term,
                    "class_section": selected_class,
                }
            )
        attrs["_target_classes"] = target_classes
        return attrs

    def create(self, validated_data):
        target_classes = validated_data.pop("_target_classes")
        school = validated_data["school"]
        batch = ReportBatch.objects.create(
            organization=school.organization,
            requested_by=self.context["request"].user,
            **validated_data,
        )
        from hamamooz.apps.students.models import Enrollment

        enrollments = Enrollment.objects.filter(
            class_section_id__in=target_classes, status=Enrollment.Status.ACTIVE
        ).select_related("student")
        ReportBatchItem.objects.bulk_create(
            [ReportBatchItem(batch=batch, enrollment=item) for item in enrollments]
        )
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


class MonthlyReportPreviewSerializer(serializers.Serializer):
    """Input for a data-driven student report without an official term.

    The provenance properties are optional request hints.  When omitted the
    report service resolves them from the source-row manifest; supplying them
    never changes imported data and is useful for an audited re-render of a
    historic workbook row.
    """

    enrollment = serializers.PrimaryKeyRelatedField(
        queryset=ReportArchive._meta.get_field("enrollment").remote_field.model.objects.all()
    )
    month_no = serializers.IntegerField(min_value=1, max_value=12)
    month_title = serializers.CharField(required=False, allow_blank=False, max_length=30)
    source_file = serializers.CharField(required=False, allow_blank=False, max_length=500)
    source_row = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        enrollment = attrs["enrollment"]
        school = enrollment.school
        if school.id not in set(accessible_school_ids(self.context["request"].user)):
            raise serializers.ValidationError("به این شعبه دسترسی ندارید.")
        if enrollment.class_section_id not in set(
            allowed_class_ids(self.context["request"].user, [school.id])
        ):
            raise serializers.ValidationError("به این کلاس دسترسی ندارید.")
        attrs.setdefault("month_title", MONTH_TITLES[attrs["month_no"]])
        return attrs


class MonthlyReportStudentSerializer(serializers.Serializer):
    name = serializers.CharField()
    national_id = serializers.CharField()
    student_number = serializers.CharField(allow_null=True)
    class_code = serializers.CharField()
    grade = serializers.CharField()
    photo_url = serializers.CharField(allow_blank=True)


class MonthlyReportMonthSerializer(serializers.Serializer):
    no = serializers.IntegerField(min_value=1, max_value=12)
    title = serializers.CharField()


class SummerSubjectResultSerializer(serializers.Serializer):
    """Representation for the independent summer subject-exam collection."""

    id = serializers.CharField(required=False, allow_null=True)
    enrollment_id = serializers.CharField()
    exam_key = serializers.CharField()
    exam_title = serializers.CharField()
    subject_code = serializers.CharField(allow_blank=True)
    subject_title = serializers.CharField()
    grade = serializers.CharField(allow_blank=True)
    class_code = serializers.CharField(allow_blank=True)
    question_count = serializers.IntegerField(allow_null=True)
    correct_count = serializers.IntegerField(allow_null=True)
    wrong_count = serializers.IntegerField(allow_null=True)
    blank_count = serializers.IntegerField(allow_null=True)
    percent = serializers.FloatField(allow_null=True)
    highest_percent = serializers.FloatField(allow_null=True)
    rank = serializers.IntegerField(allow_null=True)
    t_score = serializers.FloatField(allow_null=True)
    overall_rank = serializers.IntegerField(allow_null=True)
    score = serializers.FloatField(allow_null=True)
    final_score = serializers.FloatField(allow_null=True)
    source_file = serializers.CharField(allow_blank=True)
    source_row = serializers.IntegerField(allow_null=True)
    raw = serializers.JSONField(required=False)


class MonthlyReportContractSerializer(serializers.Serializer):
    """Stable React data contract for the summer/monthly report card."""

    report_mode = serializers.ChoiceField(choices=[ReportArchive.ReportMode.DATA_MONTHLY])
    title = serializers.CharField()
    month = MonthlyReportMonthSerializer()
    source_file = serializers.CharField(allow_blank=True)
    source_row = serializers.IntegerField(allow_null=True)
    organization = serializers.JSONField(required=False, allow_null=True)
    school = serializers.JSONField(required=False, allow_null=True)
    student = MonthlyReportStudentSerializer()
    # This collection is supplied by the independent subject-exam bounded
    # context.  It is deliberately not represented by ``subjects`` or
    # ``official_subject_grades``.
    summer_subject_results = SummerSubjectResultSerializer(many=True, required=False)
    domains = serializers.ListField(child=serializers.DictField())
    metrics = serializers.ListField(child=serializers.DictField())
    overall_score = serializers.FloatField(allow_null=True)
    completion_percent = serializers.FloatField()
    completion_status = serializers.ChoiceField(choices=["provisional", "final"])
    monthly_scores = serializers.ListField(child=serializers.DictField(), required=False)
    monthly_change = serializers.FloatField(allow_null=True)
    monthly_changes = serializers.ListField(child=serializers.DictField())
    strengths = serializers.ListField(child=serializers.DictField())
    improvements = serializers.ListField(child=serializers.DictField())
    attendance = serializers.JSONField(allow_null=True)
    activities = serializers.ListField(child=serializers.DictField())
    awards = serializers.ListField(child=serializers.DictField())
    recommendations = serializers.ListField(child=serializers.CharField())
    missing_sections = serializers.ListField(child=serializers.CharField())


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
        presentation = attrs.get("presentation", instance.presentation or {})
        if isinstance(presentation, dict):
            presentation = dict(presentation)
            with suppress(ValueError):
                presentation["page_size"] = normalize_report_page_size(
                    presentation.get("page_size")
                )
            attrs["presentation"] = presentation
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
