from rest_framework import serializers

from hamamooz.apps.accounts.access import accessible_organization_ids, accessible_school_ids

from .models import AcademicYear, ClassSection, GradeLevel, Organization, School, Term


class CleanModelSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        instance = self.instance or self.Meta.model()
        for key, value in attrs.items():
            setattr(instance, key, value)
        instance.full_clean(
            exclude=[field.name for field in instance._meta.fields if field.name == "id"]
        )
        request = self.context.get("request")
        if request:
            organization_id = None
            school_id = None
            if isinstance(instance, School | AcademicYear | GradeLevel):
                organization_id = instance.organization_id
            elif isinstance(instance, Term) and instance.academic_year_id:
                organization_id = instance.academic_year.organization_id
            elif isinstance(instance, ClassSection):
                school_id = instance.school_id
            if organization_id and organization_id not in set(
                accessible_organization_ids(request.user)
            ):
                raise serializers.ValidationError("به مجموعه انتخاب‌شده دسترسی ندارید.")
            if school_id and school_id not in set(accessible_school_ids(request.user)):
                raise serializers.ValidationError("به شعبه انتخاب‌شده دسترسی ندارید.")
        return attrs


class OrganizationSerializer(CleanModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "code", "logo", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SchoolSerializer(CleanModelSerializer):
    class Meta:
        model = School
        fields = [
            "id",
            "organization",
            "code",
            "name",
            "official_name",
            "phone",
            "email",
            "address",
            "manager_name",
            "logo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AcademicYearSerializer(CleanModelSerializer):
    class Meta:
        model = AcademicYear
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "is_deleted", "deleted_at"]


class TermSerializer(CleanModelSerializer):
    class Meta:
        model = Term
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "is_deleted", "deleted_at"]


class GradeLevelSerializer(CleanModelSerializer):
    class Meta:
        model = GradeLevel
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "is_deleted", "deleted_at"]


class ClassSectionSerializer(CleanModelSerializer):
    enrolled_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClassSection
        fields = [
            "id",
            "school",
            "academic_year",
            "grade_level",
            "code",
            "title",
            "capacity",
            "is_active",
            "enrolled_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "enrolled_count", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        capacity = attrs.get("capacity", getattr(self.instance, "capacity", 0))
        enrolled = getattr(self.instance, "enrolled_count", 0) if self.instance else 0
        if enrolled and capacity < enrolled:
            raise serializers.ValidationError({"capacity": "ظرفیت کمتر از تعداد ثبت‌نام فعال است."})
        return attrs
