from rest_framework import serializers

from hamamooz.apps.accounts.access import (
    accessible_organization_ids,
    accessible_school_ids,
    broad_access_school_ids,
)
from hamamooz.apps.students.models import Enrollment

from .models import (
    Assessment,
    AssessmentType,
    CalculationPolicy,
    CourseOffering,
    GradeSubject,
    Score,
    ScoreRevision,
    Subject,
    SubjectResult,
    TermResult,
)


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
    class Meta:
        model = Subject
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "is_deleted", "deleted_at"]

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

    class Meta:
        model = CourseOffering
        fields = [
            "id",
            "class_section",
            "class_title",
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
    class Meta:
        model = AssessmentType
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "is_deleted", "deleted_at"]

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

    class Meta:
        model = Assessment
        fields = [
            "id",
            "course_offering",
            "assessment_type",
            "assessment_type_title",
            "subject_title",
            "class_title",
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
    class Meta:
        model = CalculationPolicy
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "is_deleted", "deleted_at"]

    def validate_organization(self, value):
        if value.id not in set(accessible_organization_ids(self.context["request"].user)):
            raise serializers.ValidationError("به این مجموعه دسترسی ندارید.")
        return value


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
