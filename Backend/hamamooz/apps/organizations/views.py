from django.db.models import Count, Q

from hamamooz.apps.accounts.access import accessible_organization_ids, selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import AcademicYear, ClassSection, GradeLevel, Organization, School, Term
from .serializers import (
    AcademicYearSerializer,
    ClassSectionSerializer,
    GradeLevelSerializer,
    OrganizationSerializer,
    SchoolSerializer,
    TermSerializer,
)

ORG_ADMIN = [Role.SYSTEM_ADMIN, Role.ORGANIZATION_ADMIN]
SCHOOL_ADMIN = ORG_ADMIN + [Role.SCHOOL_MANAGER, Role.EDUCATIONAL_DEPUTY, Role.OPERATOR]


class OrganizationViewSet(AuditedModelViewSet):
    queryset = Organization.objects.none()
    serializer_class = OrganizationSerializer
    search_fields = ["name", "code"]
    required_roles_by_action = {
        "create": [Role.SYSTEM_ADMIN],
        "update": ORG_ADMIN,
        "partial_update": ORG_ADMIN,
        "destroy": [Role.SYSTEM_ADMIN],
    }

    def get_queryset(self):
        return Organization.objects.filter(id__in=accessible_organization_ids(self.request.user))


class SchoolViewSet(AuditedModelViewSet):
    queryset = School.objects.none()
    serializer_class = SchoolSerializer
    search_fields = ["name", "code", "official_name"]
    filterset_fields = ["organization", "is_active"]
    required_roles_by_action = {
        action: ORG_ADMIN for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return School.objects.filter(id__in=selected_school_ids(self.request)).select_related(
            "organization"
        )


class AcademicYearViewSet(AuditedModelViewSet):
    queryset = AcademicYear.objects.none()
    serializer_class = AcademicYearSerializer
    filterset_fields = ["organization", "is_current", "is_active"]
    required_roles_by_action = {
        action: ORG_ADMIN for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return AcademicYear.objects.filter(
            organization_id__in=accessible_organization_ids(self.request.user)
        ).select_related("organization")


class TermViewSet(AuditedModelViewSet):
    queryset = Term.objects.none()
    serializer_class = TermSerializer
    filterset_fields = ["academic_year", "code", "is_active"]
    required_roles_by_action = {
        action: ORG_ADMIN for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return Term.objects.filter(
            academic_year__organization_id__in=accessible_organization_ids(self.request.user)
        ).select_related("academic_year")


class GradeLevelViewSet(AuditedModelViewSet):
    queryset = GradeLevel.objects.none()
    serializer_class = GradeLevelSerializer
    search_fields = ["title", "code"]
    filterset_fields = ["organization", "is_active"]
    required_roles_by_action = {
        action: ORG_ADMIN for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return GradeLevel.objects.filter(
            organization_id__in=accessible_organization_ids(self.request.user)
        ).select_related("organization")


class ClassSectionViewSet(AuditedModelViewSet):
    queryset = ClassSection.objects.none()
    serializer_class = ClassSectionSerializer
    search_fields = ["title", "code"]
    filterset_fields = ["school", "academic_year", "grade_level", "is_active"]
    required_roles_by_action = {
        action: SCHOOL_ADMIN for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return (
            ClassSection.objects.filter(school_id__in=selected_school_ids(self.request))
            .select_related("school", "academic_year", "grade_level")
            .annotate(
                enrolled_count=Count(
                    "enrollments",
                    filter=Q(enrollments__status="active", enrollments__is_deleted=False),
                )
            )
        )
