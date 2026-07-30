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
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "display_name",
            "code",
            "logo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "display_name", "created_at", "updated_at"]

    def get_display_name(self, obj) -> str:
        return f"{obj.name} · کد {obj.code}"


class SchoolSerializer(CleanModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = [
            "id",
            "organization",
            "organization_name",
            "code",
            "name",
            "display_name",
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
        read_only_fields = [
            "id",
            "organization_name",
            "display_name",
            "created_at",
            "updated_at",
        ]

    def get_display_name(self, obj) -> str:
        return f"{obj.name} · {obj.organization.name} · کد {obj.code}"


class AcademicYearSerializer(CleanModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = AcademicYear
        fields = "__all__"
        read_only_fields = [
            "id",
            "organization_name",
            "created_at",
            "updated_at",
            "is_deleted",
            "deleted_at",
        ]


class TermSerializer(CleanModelSerializer):
    organization_name = serializers.CharField(
        source="academic_year.organization.name", read_only=True
    )
    academic_year_title = serializers.CharField(source="academic_year.title", read_only=True)

    class Meta:
        model = Term
        fields = "__all__"
        read_only_fields = [
            "id",
            "organization_name",
            "academic_year_title",
            "created_at",
            "updated_at",
            "is_deleted",
            "deleted_at",
        ]


class GradeLevelSerializer(CleanModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = GradeLevel
        fields = "__all__"
        read_only_fields = [
            "id",
            "organization_name",
            "created_at",
            "updated_at",
            "is_deleted",
            "deleted_at",
        ]


class ClassSectionSerializer(CleanModelSerializer):
    enrolled_count = serializers.IntegerField(read_only=True)
    school_name = serializers.CharField(source="school.name", read_only=True)
    organization_name = serializers.CharField(source="school.organization.name", read_only=True)

    class Meta:
        model = ClassSection
        fields = [
            "id",
            "school",
            "school_name",
            "organization_name",
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
        read_only_fields = [
            "id",
            "school_name",
            "organization_name",
            "enrolled_count",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        capacity = attrs.get("capacity", getattr(self.instance, "capacity", 0))
        enrolled = getattr(self.instance, "enrolled_count", 0) if self.instance else 0
        if enrolled and capacity < enrolled:
            raise serializers.ValidationError({"capacity": "ظرفیت کمتر از تعداد ثبت‌نام فعال است."})
        return attrs
