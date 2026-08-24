from rest_framework import serializers

from hamamooz.apps.accounts.access import (
    accessible_organization_ids,
    accessible_school_ids,
    broad_access_school_ids,
)
from hamamooz.apps.organizations.models import AcademicYear, School
from hamamooz.apps.students.models import Enrollment

from .models import (
    AcademicReportSettings,
    AcademicReportSettingsRevision,
    Assessment,
    AssessmentType,
    AnnualResult,
    AnnualSubjectResult,
    CalculationPolicy,
    CourseOffering,
    GradeSubject,
    Score,
    ScoreRevision,
    Subject,
    SubjectResult,
    TermResult,
)
from .services import revise_academic_report_settings


class ScopedCleanSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        instance = self.instance or self.Meta.model()
        for key, value in attrs.items():
            setattr(instance, key, value)
        exclude = ["id"]
        if not self.instance:
            exclude.extend(
                field.name
                for field in instance._meta.fields
                if field.name not in attrs
                and not field.has_default()
                and not field.null
                and not field.auto_created
            )
        instance.full_clean(exclude=exclude)
        return attrs


class SubjectSerializer(ScopedCleanSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Subject
        fields = "__all__"
        read_only_fields = [
            "id",
            "organization_name",
            "created_at",
            "updated_at",
            "is_deleted",
            "deleted_at",
        ]

    def validate_organization(self, value):
        if value.id not in set(accessible_organization_ids(self.context["request"].user)):
            raise serializers.ValidationError("به این مجموعه دسترسی ندارید.")
        return value


class GradeSubjectSerializer(ScopedCleanSerializer):
    subject_title = serializers.CharField(source="subject.title", read_only=True)
    grade_title = serializers.CharField(source="grade_level.title", read_only=True)

    class Meta:
        model = GradeSubject
        fields = [
            "id",
            "grade_level",
            "grade_title",
            "subject",
            "subject_title",
            "coefficient",
            "pass_mark",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "subject_title", "grade_title", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        grade = attrs.get("grade_level", getattr(self.instance, "grade_level", None))
        if grade and grade.organization_id not in set(
            accessible_organization_ids(self.context["request"].user)
        ):
            raise serializers.ValidationError("به مجموعه این پایه دسترسی ندارید.")
        return attrs


class CourseOfferingSerializer(ScopedCleanSerializer):
    subject_title = serializers.CharField(source="grade_subject.subject.title", read_only=True)
    class_title = serializers.CharField(source="class_section.title", read_only=True)
    teacher_name = serializers.CharField(source="teacher.get_full_name", read_only=True)
    term_title = serializers.CharField(source="term.title", read_only=True)
    school_name = serializers.CharField(source="class_section.school.name", read_only=True)
    organization_name = serializers.CharField(
        source="class_section.school.organization.name", read_only=True
    )

    class Meta:
        model = CourseOffering
        fields = [
            "id",
            "class_section",
            "class_title",
            "school_name",
            "organization_name",
            "grade_subject",
            "subject_title",
            "term",
            "term_title",
            "teacher",
            "teacher_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "class_title",
            "school_name",
            "organization_name",
            "subject_title",
            "term_title",
            "teacher_name",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        class_section = attrs.get("class_section", getattr(self.instance, "class_section", None))
        if class_section and class_section.school_id not in set(
            accessible_school_ids(self.context["request"].user)
        ):
            raise serializers.ValidationError("به شعبه این کلاس دسترسی ندارید.")
        if self.instance:
            structural = {"class_section", "grade_subject", "term"}
            changed = {
                field
                for field in structural
                if field in attrs and attrs[field] != getattr(self.instance, field)
            }
            if changed and (
                self.instance.assessments.exists() or self.instance.attendance_sessions.exists()
            ):
                raise serializers.ValidationError(
                    "کلاس، درس و نوبتِ ارائه دارای سابقه قابل تغییر نیستند."
                )
        teacher = attrs.get("teacher", getattr(self.instance, "teacher", None))
        if class_section and teacher:
            from hamamooz.apps.accounts.models import Role, RoleAssignment

            if not RoleAssignment.objects.filter(
                user=teacher,
                school=class_section.school,
                role=Role.TEACHER,
                is_active=True,
            ).exists():
                raise serializers.ValidationError(
                    {"teacher": "کاربر انتخاب‌شده نقش دبیر فعال در این شعبه ندارد."}
                )
        return attrs


class AssessmentTypeSerializer(ScopedCleanSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = AssessmentType
        fields = "__all__"
        read_only_fields = [
            "id",
            "organization_name",
            "created_at",
            "updated_at",
            "is_deleted",
            "deleted_at",
        ]

    def validate_organization(self, value):
        if value.id not in set(accessible_organization_ids(self.context["request"].user)):
            raise serializers.ValidationError("به این مجموعه دسترسی ندارید.")
        return value


class ScoreRevisionSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.get_full_name", read_only=True)

    class Meta:
        model = ScoreRevision
        fields = "__all__"


class ScoreSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)
    student_number = serializers.CharField(source="enrollment.student_number", read_only=True)
    history = ScoreRevisionSerializer(many=True, read_only=True)

    class Meta:
        model = Score
        fields = [
            "id",
            "assessment",
            "enrollment",
            "student_name",
            "student_number",
            "value",
            "status",
            "note",
            "recorded_by",
            "revision",
            "history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AssessmentSerializer(ScopedCleanSerializer):
    assessment_type_title = serializers.CharField(source="assessment_type.title", read_only=True)
    subject_title = serializers.CharField(
        source="course_offering.grade_subject.subject.title", read_only=True
    )
    class_title = serializers.CharField(
        source="course_offering.class_section.title", read_only=True
    )
    teacher_name = serializers.CharField(
        source="course_offering.teacher.get_full_name", read_only=True
    )
    score_count = serializers.IntegerField(read_only=True)
    school_name = serializers.CharField(
        source="course_offering.class_section.school.name", read_only=True
    )
    organization_name = serializers.CharField(
        source="course_offering.class_section.school.organization.name", read_only=True
    )

    class Meta:
        model = Assessment
        fields = [
            "id",
            "course_offering",
            "assessment_type",
            "assessment_type_title",
            "subject_title",
            "class_title",
            "school_name",
            "organization_name",
            "teacher_name",
            "title",
            "assessment_date",
            "max_score",
            "weight",
            "status",
            "created_by",
            "submitted_at",
            "reviewed_at",
            "reviewed_by",
            "locked_at",
            "rejection_reason",
            "workflow_version",
            "score_count",
            "school_name",
            "organization_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_by",
            "submitted_at",
            "reviewed_at",
            "reviewed_by",
            "locked_at",
            "rejection_reason",
            "workflow_version",
            "score_count",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        offering = attrs.get("course_offering", getattr(self.instance, "course_offering", None))
        request = self.context["request"]
        if offering and offering.class_section.school_id not in set(
            accessible_school_ids(request.user)
        ):
            raise serializers.ValidationError("به شعبه این درس دسترسی ندارید.")
        if offering and offering.teacher_id != request.user.id:
            broad = broad_access_school_ids(request.user, [offering.class_section.school_id])
            if offering.class_section.school_id not in set(broad):
                raise serializers.ValidationError(
                    "دبیر فقط برای درس‌های خودش می‌تواند ارزیابی بسازد."
                )
        if self.instance and self.instance.scores.exists():
            structural = {"course_offering", "assessment_type", "max_score"}
            changed = {
                field
                for field in structural
                if field in attrs and attrs[field] != getattr(self.instance, field)
            }
            if changed:
                raise serializers.ValidationError("ساختار ارزیابی پس از ثبت نمره قابل تغییر نیست.")
        if self.instance and self.instance.status not in [
            Assessment.Status.DRAFT,
            Assessment.Status.REJECTED,
        ]:
            editable = {
                "title",
                "assessment_date",
                "max_score",
                "weight",
                "assessment_type",
                "course_offering",
            }
            if editable.intersection(attrs):
                raise serializers.ValidationError("ارزیابی ارسال‌شده قابل ویرایش مستقیم نیست.")
        return attrs

    def create(self, validated_data):
        validated_data.setdefault("weight", validated_data["assessment_type"].default_weight)
        return super().create(validated_data)


class ScoreEntrySerializer(serializers.Serializer):
    enrollment = serializers.PrimaryKeyRelatedField(queryset=Enrollment.objects.all())
    value = serializers.DecimalField(
        max_digits=7, decimal_places=2, required=False, allow_null=True
    )
    status = serializers.ChoiceField(choices=Score.Status.choices)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class BulkScoreSerializer(serializers.Serializer):
    entries = ScoreEntrySerializer(many=True, allow_empty=False)


class RejectAssessmentSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3)


class CorrectLockedScoreSerializer(serializers.Serializer):
    value = serializers.DecimalField(
        max_digits=7, decimal_places=2, required=False, allow_null=True, default=None
    )
    status = serializers.ChoiceField(choices=Score.Status.choices)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    reason = serializers.CharField(min_length=5)


class CalculationPolicySerializer(ScopedCleanSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance:
            immutable = {"organization", "academic_year", "grade_level", "version"}
            changed = {
                field
                for field in immutable
                if field in attrs and attrs[field] != getattr(self.instance, field)
            }
            if changed:
                raise serializers.ValidationError(
                    "دامنه و نسخه سیاست محاسبه پس از ایجاد قابل تغییر نیست."
                )
        return attrs

    class Meta:
        model = CalculationPolicy
        fields = "__all__"
        read_only_fields = [
            "id",
            "organization_name",
            "created_at",
            "updated_at",
            "is_deleted",
            "deleted_at",
        ]

    def validate_organization(self, value):
        if value.id not in set(accessible_organization_ids(self.context["request"].user)):
            raise serializers.ValidationError("به این مجموعه دسترسی ندارید.")
        return value


class AcademicReportSettingsRevisionSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.get_full_name", read_only=True)

    class Meta:
        model = AcademicReportSettingsRevision
        fields = [
            "id",
            "revision",
            "changed_by",
            "changed_by_name",
            "reason",
            "before",
            "after",
            "created_at",
        ]
        read_only_fields = fields


class AcademicReportSettingsSerializer(ScopedCleanSerializer):
    school_name = serializers.CharField(source="school.name", read_only=True)
    academic_year_title = serializers.CharField(source="academic_year.title", read_only=True)
    reason = serializers.CharField(
        write_only=True,
        required=False,
        min_length=5,
        max_length=500,
    )
    history = AcademicReportSettingsRevisionSerializer(many=True, read_only=True)

    class Meta:
        model = AcademicReportSettings
        fields = [
            "id",
            "school",
            "school_name",
            "academic_year",
            "academic_year_title",
            "first_term_weight",
            "second_term_weight",
            "show_class_rank",
            "show_grade_rank",
            "show_school_rank",
            "revision",
            "reason",
            "history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "school_name",
            "academic_year_title",
            "revision",
            "history",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context["request"]
        school = attrs.get("school", getattr(self.instance, "school", None))
        academic_year = attrs.get(
            "academic_year", getattr(self.instance, "academic_year", None)
        )
        if school and school.id not in set(accessible_school_ids(request.user)):
            raise serializers.ValidationError({"school": "به این شعبه دسترسی ندارید."})
        if (
            school
            and academic_year
            and school.organization_id != academic_year.organization_id
        ):
            raise serializers.ValidationError(
                {"academic_year": "سال تحصیلی متعلق به مجموعه این شعبه نیست."}
            )
        if self.instance:
            changed_scope = {
                field
                for field in ["school", "academic_year"]
                if field in attrs and attrs[field] != getattr(self.instance, field)
            }
            if changed_scope:
                raise serializers.ValidationError("شعبه و سال تحصیلی پس از ایجاد قابل تغییر نیستند.")
            if not attrs.get("reason", "").strip():
                raise serializers.ValidationError({"reason": "دلیل تغییر الزامی است."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("reason", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        reason = validated_data.pop("reason")
        return revise_academic_report_settings(
            settings=instance,
            changes=validated_data,
            reason=reason,
            actor=self.context["request"].user,
            request=self.context["request"],
        )


class SubjectResultSerializer(serializers.ModelSerializer):
    subject_title = serializers.CharField(
        source="course_offering.grade_subject.subject.title", read_only=True
    )
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)

    class Meta:
        model = SubjectResult
        fields = "__all__"


class TermResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)

    class Meta:
        model = TermResult
        fields = "__all__"


class AnnualSubjectResultSerializer(serializers.ModelSerializer):
    subject_title = serializers.CharField(source="grade_subject.subject.title", read_only=True)
    coefficient = serializers.DecimalField(
        source="grade_subject.coefficient", max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = AnnualSubjectResult
        fields = [
            "id",
            "enrollment",
            "grade_subject",
            "subject_title",
            "coefficient",
            "average",
            "complete",
            "passed",
            "formula_version",
            "calculated_at",
        ]
        read_only_fields = fields


class AnnualResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)
    class_title = serializers.CharField(source="enrollment.class_section.title", read_only=True)
    grade_title = serializers.CharField(source="enrollment.grade_level.title", read_only=True)
    school_name = serializers.CharField(source="enrollment.school.name", read_only=True)
    academic_year_title = serializers.CharField(
        source="enrollment.academic_year.title", read_only=True
    )
    subject_results = AnnualSubjectResultSerializer(many=True, read_only=True)

    class Meta:
        model = AnnualResult
        fields = [
            "id",
            "enrollment",
            "student_name",
            "school_name",
            "academic_year_title",
            "grade_title",
            "class_title",
            "average",
            "class_rank",
            "grade_rank",
            "school_rank",
            "class_population",
            "grade_population",
            "school_population",
            "complete",
            "passed",
            "formula_version",
            "calculated_at",
            "subject_results",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RecalculateAnnualResultsSerializer(serializers.Serializer):
    school = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.all()
    )
    academic_year = serializers.PrimaryKeyRelatedField(
        queryset=AcademicYear.objects.all()
    )

    def validate(self, attrs):
        request = self.context["request"]
        school = attrs["school"]
        academic_year = attrs["academic_year"]
        if school.id not in set(accessible_school_ids(request.user)):
            raise serializers.ValidationError({"school": "به این شعبه دسترسی ندارید."})
        if school.organization_id != academic_year.organization_id:
            raise serializers.ValidationError(
                {"academic_year": "سال تحصیلی متعلق به مجموعه این شعبه نیست."}
            )
        return attrs
