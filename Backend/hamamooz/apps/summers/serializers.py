from rest_framework import serializers

from hamamooz.apps.accounts.access import selected_school_ids

from .models import (
    SummerComprehensiveExam,
    SummerCourse,
    SummerCourseRegistration,
    SummerProgram,
    SummerProgramRevision,
    SummerRegistration,
    SummerSubjectScore,
)


def _validate_selected_scope(instance, request):
    if request and instance.school_id not in set(selected_school_ids(request)):
        raise serializers.ValidationError("رکورد خارج از شعبه انتخاب‌شده است.")


class ScopedModelSerializer(serializers.ModelSerializer):
    immutable_fields = set()

    def build_validation_instance(self, attrs):
        return self.instance or self.Meta.model()

    def validate(self, attrs):
        if self.instance:
            changed = {
                field
                for field in self.immutable_fields
                if field in attrs and attrs[field] != getattr(self.instance, field)
            }
            if changed:
                raise serializers.ValidationError(
                    {field: "این رابطه پس از ایجاد قابل تغییر نیست." for field in changed}
                )
        instance = self.build_validation_instance(attrs)
        original = {}
        if self.instance:
            original = {field: getattr(instance, field) for field in attrs}
        try:
            for field, value in attrs.items():
                setattr(instance, field, value)
            instance.full_clean(exclude=["id"])
            _validate_selected_scope(instance, self.context.get("request"))
        finally:
            for field, value in original.items():
                setattr(instance, field, value)
        return attrs


class SummerProgramRevisionSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True)

    class Meta:
        model = SummerProgramRevision
        fields = [
            "id",
            "program",
            "actor",
            "actor_name",
            "old_pass_threshold",
            "new_pass_threshold",
            "reason",
            "created_at",
        ]
        read_only_fields = fields


class SummerProgramSerializer(ScopedModelSerializer):
    school_name = serializers.CharField(source="school.name", read_only=True)
    academic_year_title = serializers.CharField(source="academic_year.title", read_only=True)
    threshold_change_reason = serializers.CharField(
        write_only=True, required=False, allow_blank=False, max_length=500
    )
    immutable_fields = {"school", "academic_year"}

    class Meta:
        model = SummerProgram
        fields = [
            "id",
            "school",
            "school_name",
            "academic_year",
            "academic_year_title",
            "title",
            "pass_threshold",
            "threshold_change_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "school_name",
            "academic_year_title",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        reason = attrs.pop("threshold_change_reason", None)
        current = self.instance.pass_threshold if self.instance else None
        replacement = attrs.get("pass_threshold", current)
        if self.instance and replacement != current and not reason:
            raise serializers.ValidationError(
                {"threshold_change_reason": "دلیل تغییر حد قبولی الزامی است."}
            )
        attrs = super().validate(attrs)
        if reason is not None:
            attrs["threshold_change_reason"] = reason
        return attrs

    def create(self, validated_data):
        validated_data.pop("threshold_change_reason", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        reason = validated_data.pop("threshold_change_reason", "")
        locked = SummerProgram.objects.select_for_update().get(pk=instance.pk)
        old_threshold = locked.pass_threshold
        updated = super().update(locked, validated_data)
        if updated.pass_threshold != old_threshold:
            SummerProgramRevision.objects.create(
                program=updated,
                actor=self.context["request"].user,
                old_pass_threshold=old_threshold,
                new_pass_threshold=updated.pass_threshold,
                reason=reason,
            )
        return updated


class SummerCourseSerializer(ScopedModelSerializer):
    subject_title = serializers.CharField(source="subject.title", read_only=True)
    coefficient = serializers.DecimalField(
        source="subject.default_coefficient", max_digits=5, decimal_places=2, read_only=True
    )
    immutable_fields = {"program", "subject"}

    class Meta:
        model = SummerCourse
        fields = [
            "id",
            "program",
            "subject",
            "subject_title",
            "coefficient",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "subject_title", "coefficient", "created_at", "updated_at"]


class SummerRegistrationSerializer(ScopedModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)
    grade_title = serializers.CharField(source="enrollment.grade_level.title", read_only=True)
    class_title = serializers.CharField(source="enrollment.class_section.title", read_only=True)
    immutable_fields = {"program", "enrollment"}

    class Meta:
        model = SummerRegistration
        fields = [
            "id",
            "program",
            "enrollment",
            "student_name",
            "grade_title",
            "class_title",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student_name",
            "grade_title",
            "class_title",
            "created_at",
            "updated_at",
        ]


class SummerCourseRegistrationSerializer(ScopedModelSerializer):
    student_name = serializers.CharField(
        source="registration.enrollment.student.full_name", read_only=True
    )
    subject_title = serializers.CharField(source="course.subject.title", read_only=True)
    immutable_fields = {"registration", "course"}

    class Meta:
        model = SummerCourseRegistration
        fields = [
            "id",
            "registration",
            "course",
            "student_name",
            "subject_title",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student_name",
            "subject_title",
            "created_at",
            "updated_at",
        ]


class SummerComprehensiveExamSerializer(ScopedModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    finalized_by_name = serializers.CharField(
        source="finalized_by.get_full_name", read_only=True, allow_null=True
    )
    immutable_fields = {"program"}

    class Meta:
        model = SummerComprehensiveExam
        fields = [
            "id",
            "program",
            "title",
            "exam_date",
            "status",
            "status_display",
            "finalized_at",
            "finalized_by",
            "finalized_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "status_display",
            "finalized_at",
            "finalized_by",
            "finalized_by_name",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        if self.instance and self.instance.status == SummerComprehensiveExam.Status.FINALIZED:
            raise serializers.ValidationError("آزمون جامع نهایی‌شده قابل ویرایش نیست.")
        return super().validate(attrs)


class SummerSubjectScoreSerializer(ScopedModelSerializer):
    student_name = serializers.CharField(
        source="course_registration.registration.enrollment.student.full_name", read_only=True
    )
    subject_title = serializers.CharField(
        source="course_registration.course.subject.title", read_only=True
    )
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)
    immutable_fields = {"exam", "course_registration"}

    class Meta:
        model = SummerSubjectScore
        fields = [
            "id",
            "exam",
            "course_registration",
            "student_name",
            "subject_title",
            "value",
            "recorded_by",
            "recorded_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student_name",
            "subject_title",
            "recorded_by",
            "recorded_by_name",
            "created_at",
            "updated_at",
        ]

    def build_validation_instance(self, attrs):
        return self.instance or SummerSubjectScore(recorded_by=self.context["request"].user)

    def validate(self, attrs):
        exam = attrs.get("exam", self.instance.exam if self.instance else None)
        if exam and exam.status != SummerComprehensiveExam.Status.DRAFT:
            raise serializers.ValidationError("نمره آزمون جامع نهایی‌شده قابل تغییر نیست.")
        return super().validate(attrs)
