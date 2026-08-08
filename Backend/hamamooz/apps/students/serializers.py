from rest_framework import serializers

from hamamooz.apps.accounts.access import accessible_organization_ids, accessible_school_ids

from .models import Enrollment, EnrollmentEvent, Guardian, Student, StudentGuardian
from .services import create_enrollment


class StudentGuardianSerializer(serializers.ModelSerializer):
    guardian_name = serializers.CharField(source="guardian.full_name", read_only=True)

    class Meta:
        model = StudentGuardian
        fields = ["id", "guardian", "guardian_name", "relationship", "is_primary", "can_pick_up"]


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    guardians = StudentGuardianSerializer(source="guardian_links", many=True, read_only=True)

    class Meta:
        model = Student
        fields = [
            "id",
            "organization",
            "organization_name",
            "national_id",
            "first_name",
            "last_name",
            "full_name",
            "birth_date",
            "gender",
            "status",
            "photo",
            "notes",
            "guardians",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization_name",
            "full_name",
            "status",
            "guardians",
            "created_at",
            "updated_at",
        ]

    def validate_organization(self, value):
        if self.instance and value.pk != self.instance.organization_id:
            raise serializers.ValidationError("مجموعه دانش‌آموز پس از ایجاد قابل تغییر نیست.")
        request = self.context.get("request")
        if request and value.id not in set(accessible_organization_ids(request.user)):
            raise serializers.ValidationError("به این مجموعه دسترسی ندارید.")
        return value


class GuardianSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    students = StudentGuardianSerializer(source="student_links", many=True, read_only=True)

    class Meta:
        model = Guardian
        fields = [
            "id",
            "organization",
            "organization_name",
            "national_id",
            "first_name",
            "last_name",
            "full_name",
            "phone_primary",
            "phone_secondary",
            "email",
            "address",
            "students",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization_name",
            "full_name",
            "students",
            "created_at",
            "updated_at",
        ]

    def validate_organization(self, value):
        if self.instance and value.pk != self.instance.organization_id:
            raise serializers.ValidationError("مجموعه ولی پس از ایجاد قابل تغییر نیست.")
        request = self.context.get("request")
        if request and value.id not in set(accessible_organization_ids(request.user)):
            raise serializers.ValidationError("به این مجموعه دسترسی ندارید.")
        return value


class EnrollmentEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True)

    class Meta:
        model = EnrollmentEvent
        fields = "__all__"


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    school_name = serializers.CharField(source="school.name", read_only=True)
    organization_name = serializers.CharField(source="school.organization.name", read_only=True)
    grade_title = serializers.CharField(source="grade_level.title", read_only=True)
    class_title = serializers.CharField(source="class_section.title", read_only=True)
    events = EnrollmentEventSerializer(many=True, read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "student",
            "student_name",
            "school",
            "school_name",
            "organization_name",
            "academic_year",
            "grade_level",
            "grade_title",
            "class_section",
            "class_title",
            "student_number",
            "status",
            "enrolled_on",
            "left_on",
            "events",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student_name",
            "school_name",
            "organization_name",
            "grade_title",
            "class_title",
            "events",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        if self.instance:
            protected = {
                "student",
                "school",
                "academic_year",
                "grade_level",
                "class_section",
                "student_number",
                "status",
                "enrolled_on",
                "left_on",
            }
            changed = [
                key
                for key in protected
                if key in attrs and attrs[key] != getattr(self.instance, key)
            ]
            if changed:
                raise serializers.ValidationError(
                    "تغییر کلاس، انتقال و وضعیت باید از عملیات اختصاصی مربوط انجام شود."
                )
        school = attrs.get("school", getattr(self.instance, "school", None))
        if school:
            request = self.context.get("request")
            if request and school.id not in set(accessible_school_ids(request.user)):
                raise serializers.ValidationError({"school": "به این شعبه دسترسی ندارید."})
        instance = self.instance or Enrollment()
        for key, value in attrs.items():
            setattr(instance, key, value)
        instance.full_clean(exclude=["id"])
        if not self.instance and instance.status == Enrollment.Status.ACTIVE:
            count = Enrollment.objects.filter(
                class_section=instance.class_section, status=Enrollment.Status.ACTIVE
            ).count()
            if count >= instance.class_section.capacity:
                raise serializers.ValidationError({"class_section": "ظرفیت کلاس تکمیل است."})
        return attrs

    def create(self, validated_data):
        return create_enrollment(**validated_data)


class LinkGuardianSerializer(serializers.Serializer):
    guardian = serializers.PrimaryKeyRelatedField(queryset=Guardian.objects.all())
    relationship = serializers.ChoiceField(choices=StudentGuardian.Relationship.choices)
    is_primary = serializers.BooleanField(default=False)
    can_pick_up = serializers.BooleanField(default=False)

    def validate(self, attrs):
        student = self.context["student"]
        if attrs["guardian"].organization_id != student.organization_id:
            raise serializers.ValidationError("ولی و دانش‌آموز باید متعلق به یک مجموعه باشند.")
        return attrs


class ChangeClassSerializer(serializers.Serializer):
    class_section = serializers.PrimaryKeyRelatedField(
        queryset=Enrollment._meta.get_field("class_section").remote_field.model.objects.all()
    )
    effective_date = serializers.DateField(required=False)
    reason = serializers.CharField(min_length=3)


class TransferEnrollmentSerializer(serializers.Serializer):
    school = serializers.PrimaryKeyRelatedField(
        queryset=Enrollment._meta.get_field("school").remote_field.model.objects.all()
    )
    grade_level = serializers.PrimaryKeyRelatedField(
        queryset=Enrollment._meta.get_field("grade_level").remote_field.model.objects.all()
    )
    class_section = serializers.PrimaryKeyRelatedField(
        queryset=Enrollment._meta.get_field("class_section").remote_field.model.objects.all()
    )
    student_number = serializers.CharField(max_length=50)
    transfer_date = serializers.DateField()
    reason = serializers.CharField(min_length=3)

    def validate(self, attrs):
        request = self.context.get("request")
        if request and attrs["school"].id not in set(accessible_school_ids(request.user)):
            raise serializers.ValidationError({"school": "به شعبه مقصد دسترسی ندارید."})
        return attrs


class ChangeEnrollmentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            Enrollment.Status.WITHDRAWN,
            Enrollment.Status.GRADUATED,
        ]
    )
    date = serializers.DateField()
    reason = serializers.CharField(min_length=3)
