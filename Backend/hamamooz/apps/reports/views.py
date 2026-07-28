from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from rest_framework.decorators import action
from rest_framework.response import Response

from hamamooz.apps.accounts.access import allowed_class_ids, selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.services import record_audit
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import ReportArchive
from .serializers import ReportArchiveSerializer, ReportPreviewSerializer
from .services import build_report_snapshot, render_report_html
from .tasks import generate_report_task

REPORTERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
    Role.OPERATOR,
    Role.TEACHER,
]


class ReportArchiveViewSet(AuditedModelViewSet):
    queryset = ReportArchive.objects.none()
    serializer_class = ReportArchiveSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = [
        "school",
        "academic_year",
        "term",
        "report_type",
        "status",
        "enrollment",
        "class_section",
    ]
    required_roles_by_action = {"create": REPORTERS, "preview": REPORTERS}

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids(self.request.user, school_ids)
        queryset = ReportArchive.objects.filter(school_id__in=school_ids).filter(
            Q(class_section_id__in=class_ids) | Q(enrollment__class_section_id__in=class_ids)
        )
        return queryset.select_related(
            "school",
            "academic_year",
            "term",
            "enrollment__student",
            "class_section",
            "requested_by",
        ).distinct()

    def perform_create(self, serializer):
        report = self.perform_audited_create(
            serializer,
            action="report.queued",
            metadata=lambda instance: {"report_type": instance.report_type},
        )
        transaction.on_commit(lambda: generate_report_task.delay(str(report.id)))

    @action(detail=False, methods=["post"])
    def preview(self, request):
        serializer = ReportPreviewSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        snapshot = build_report_snapshot(
            data["report_type"],
            data["term"],
            enrollment=data.get("enrollment"),
            class_section=data.get("class_section"),
        )
        return Response({"html": render_report_html(snapshot, preview=True), "snapshot": snapshot})

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        report = self.get_object()
        if report.status != ReportArchive.Status.COMPLETED or not report.output_file:
            return Response({"detail": "فایل گزارش هنوز آماده نیست."}, status=409)
        record_audit(
            action="report.downloaded",
            actor=request.user,
            request=request,
            entity=report,
            organization_id=report.organization_id,
            school_id=report.school_id,
        )
        report.output_file.open("rb")
        return FileResponse(
            report.output_file,
            as_attachment=True,
            filename=f"hamamooz-report-{report.id}.pdf",
            content_type="application/pdf",
        )
