from django.db import transaction

from hamamooz.apps.accounts.access import allowed_class_ids_for_roles, selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .engine import run_for_enrollment
from .models import AnalyticsRuleConfig, AnalyticsRun, OperationalAlert, StudentRiskSignal
from .permissions import ANALYTICS_MANAGERS
from .serializers import (
    AnalyticsRuleConfigSerializer,
    AnalyticsRunCreateSerializer,
    AnalyticsRunSerializer,
    OperationalAlertSerializer,
    StudentRiskSignalSerializer,
)


class AnalyticsRuleConfigViewSet(AuditedModelViewSet):
    queryset = AnalyticsRuleConfig.objects.none()
    serializer_class = AnalyticsRuleConfigSerializer
    filterset_fields = ["organization", "rule_code", "enabled"]
    required_roles_by_action = {
        action: ANALYTICS_MANAGERS for action in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        from hamamooz.apps.accounts.access import accessible_organization_ids

        return AnalyticsRuleConfig.objects.filter(
            organization_id__in=accessible_organization_ids(self.request.user)
        )


class AnalyticsRunViewSet(AuditedModelViewSet):
    queryset = AnalyticsRun.objects.none()
    filterset_fields = ["school", "enrollment", "status", "trigger"]
    ordering_fields = ["created_at", "completed_at"]
    http_method_names = ["get", "post", "head", "options"]
    required_roles_by_action = {"create": ANALYTICS_MANAGERS}

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids_for_roles(
            self.request.user, school_ids, [Role.STUDENT_AFFAIRS_DEPUTY]
        )
        return AnalyticsRun.objects.filter(
            school_id__in=school_ids, enrollment__class_section_id__in=class_ids
        )

    def get_serializer_class(self):
        return AnalyticsRunCreateSerializer if self.action == "create" else AnalyticsRunSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            run = run_for_enrollment(
                enrollment_id=serializer.validated_data["enrollment"].id,
                trigger=serializer.validated_data.get("trigger", AnalyticsRun.Trigger.MANUAL),
                requested_by=request.user,
            )
        return self.get_response(run)

    def get_response(self, run):
        from rest_framework import status
        from rest_framework.response import Response

        return Response(AnalyticsRunSerializer(run).data, status=status.HTTP_201_CREATED)


class StudentRiskSignalViewSet(AuditedModelViewSet):
    queryset = StudentRiskSignal.objects.none()
    serializer_class = StudentRiskSignalSerializer
    http_method_names = ["get", "head", "options"]
    filterset_fields = ["school", "enrollment", "rule_code", "severity", "state"]
    ordering_fields = ["created_at", "severity"]

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids_for_roles(
            self.request.user, school_ids, [Role.STUDENT_AFFAIRS_DEPUTY]
        )
        return StudentRiskSignal.objects.filter(
            school_id__in=school_ids, enrollment__class_section_id__in=class_ids
        ).select_related("enrollment__student", "run")


class OperationalAlertViewSet(AuditedModelViewSet):
    queryset = OperationalAlert.objects.none()
    serializer_class = OperationalAlertSerializer
    http_method_names = ["get", "head", "options"]
    filterset_fields = ["status", "signal"]

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids_for_roles(
            self.request.user, school_ids, [Role.STUDENT_AFFAIRS_DEPUTY]
        )
        return OperationalAlert.objects.filter(
            signal__school_id__in=school_ids,
            signal__enrollment__class_section_id__in=class_ids,
        ).select_related("signal__enrollment__student")
