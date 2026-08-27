from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from hamamooz.apps.accounts.access import allowed_class_ids, selected_school_ids
from hamamooz.apps.accounts.models import Role
from hamamooz.apps.core.services import record_audit
from hamamooz.apps.core.viewsets import AuditedModelViewSet

from .models import ReportArchive, ReportBatch, ReportDraft, ReportTemplate
from .serializers import (
    ReportArchiveSerializer,
    ReportBatchCreateSerializer,
    ReportBatchSerializer,
    ReportDraftContentSerializer,
    ReportDraftCreateSerializer,
    ReportDraftSerializer,
    ReportDraftTransitionSerializer,
    ReportPreviewSerializer,
    ReportTemplateSerializer,
)
from .services import build_report_snapshot, render_report_draft, render_report_html
from .tasks import generate_report_batch_task, generate_report_task

REPORTERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
    Role.OPERATOR,
    Role.TEACHER,
]
REPORT_REVIEWERS = [
    Role.SYSTEM_ADMIN,
    Role.ORGANIZATION_ADMIN,
    Role.SCHOOL_MANAGER,
    Role.EDUCATIONAL_DEPUTY,
]


def _safe_filename_part(value):
    return (
        str(value).replace("/", "-").replace("\\", "-").replace("\r", "").replace("\n", "").strip()
    )


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
    required_roles_by_action = {
        "create": REPORTERS,
        "preview": REPORTERS,
        "release": REPORT_REVIEWERS,
    }

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
        extension = "docx" if report.output_format == ReportArchive.OutputFormat.DOCX else "pdf"
        content_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if extension == "docx"
            else "application/pdf"
        )
        return FileResponse(
            report.output_file,
            as_attachment=True,
            filename=(
                f"{_safe_filename_part(report.organization.name)}-"
                f"{_safe_filename_part(report.school.name)}-"
                f"{_safe_filename_part(report.get_report_type_display())}-"
                f"{report.created_at:%Y-%m-%d}.{extension}"
            ),
            content_type=content_type,
        )

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        report = self.get_object()
        if report.status != ReportArchive.Status.COMPLETED:
            return Response({"detail": "Only a completed report may be released."}, status=409)
        if report.released_at:
            return Response(ReportArchiveSerializer(report, context={"request": request}).data)
        report.released_by = request.user
        report.released_at = timezone.now()
        report.save(update_fields=["released_by", "released_at", "updated_at"])
        record_audit(
            action="report.released",
            actor=request.user,
            request=request,
            entity=report,
            organization_id=report.organization_id,
            school_id=report.school_id,
        )
        return Response(ReportArchiveSerializer(report, context={"request": request}).data)


class ReportBatchViewSet(AuditedModelViewSet):
    queryset = ReportBatch.objects.none()
    serializer_class = ReportBatchSerializer
    http_method_names = ["get", "post", "head", "options"]
    required_roles_by_action = {"create": REPORTERS, "release": REPORT_REVIEWERS}

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids(self.request.user, school_ids)
        return (ReportBatch.objects.filter(school_id__in=school_ids)
                .filter(Q(scope=ReportBatch.Scope.SCHOOL) | Q(class_section_id__in=class_ids))
                .select_related("school", "academic_year", "term", "class_section", "requested_by")
                .prefetch_related("items__enrollment__student", "items__report"))

    def create(self, request, *args, **kwargs):
        serializer = ReportBatchCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        batch = serializer.save()
        record_audit(action="report.batch_queued", actor=request.user, request=request, entity=batch,
                     organization_id=batch.organization_id, school_id=batch.school_id,
                     metadata={"scope": batch.scope, "total_count": batch.total_count})
        transaction.on_commit(lambda: generate_report_batch_task.delay(str(batch.id)))
        return Response(ReportBatchSerializer(batch, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        batch = self.get_object()
        if not batch.zip_file:
            return Response({"detail": "Batch ZIP is not ready."}, status=409)
        batch.zip_file.open("rb")
        return FileResponse(batch.zip_file, as_attachment=True, filename=f"report-batch-{batch.id}.zip", content_type="application/zip")

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        batch = self.get_object()
        ReportArchive.objects.filter(batch_item__batch=batch, status=ReportArchive.Status.COMPLETED, released_at__isnull=True).update(released_by=request.user, released_at=timezone.now())
        record_audit(action="report.batch_released", actor=request.user, request=request, entity=batch,
                     organization_id=batch.organization_id, school_id=batch.school_id)
        return Response(ReportBatchSerializer(batch, context={"request": request}).data)


class ReportTemplateViewSet(AuditedModelViewSet):
    queryset = ReportTemplate.objects.none()
    serializer_class = ReportTemplateSerializer
    filterset_fields = ["organization", "school", "report_type", "output_format", "is_active"]
    search_fields = ["code", "title"]
    required_roles_by_action = {
        action_name: REPORT_REVIEWERS
        for action_name in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        from hamamooz.apps.accounts.access import accessible_organization_ids

        return ReportTemplate.objects.filter(
            organization_id__in=accessible_organization_ids(self.request.user)
        ).filter(Q(school__isnull=True) | Q(school_id__in=school_ids))


class ReportDraftViewSet(AuditedModelViewSet):
    queryset = ReportDraft.objects.none()
    serializer_class = ReportDraftSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["school", "academic_year", "term", "enrollment", "class_section", "status"]
    ordering_fields = ["created_at", "reviewed_at"]
    required_roles_by_action = {
        "create": REPORTERS,
        "partial_update": REPORTERS,
        "submit": REPORTERS,
        "approve": REPORT_REVIEWERS,
        "reject": REPORT_REVIEWERS,
        "render": REPORT_REVIEWERS,
    }

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids(self.request.user, school_ids)
        return (
            ReportDraft.objects.filter(school_id__in=school_ids)
            .filter(
                Q(enrollment__class_section_id__in=class_ids) | Q(class_section_id__in=class_ids)
            )
            .select_related("template", "enrollment__student", "class_section", "archive")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ReportDraftCreateSerializer
        return ReportDraftSerializer

    def create(self, request, *args, **kwargs):
        serializer = ReportDraftCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        draft = serializer.save()
        record_audit(
            action="report.draft_created",
            actor=request.user,
            request=request,
            entity=draft,
            organization_id=draft.organization_id,
            school_id=draft.school_id,
            metadata={"template": draft.template.code, "snapshot_version": "full_product_v1"},
        )
        return Response(ReportDraftSerializer(draft).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        draft = self.get_object()
        if draft.status != ReportDraft.Status.DRAFT:
            raise PermissionDenied("Only a draft report may be edited.")
        serializer = ReportDraftContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        draft.content_overrides = serializer.validated_data["content_overrides"]
        draft.save(update_fields=["content_overrides", "updated_at"])
        record_audit(
            action="report.draft_edited",
            actor=request.user,
            request=request,
            entity=draft,
            organization_id=draft.organization_id,
            school_id=draft.school_id,
            metadata={"scope": "allowlisted_content_overrides"},
        )
        return Response(ReportDraftSerializer(draft).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        draft = self.get_object()
        if draft.status != ReportDraft.Status.DRAFT:
            return Response({"detail": "Only a draft report may be submitted."}, status=409)
        draft.status = ReportDraft.Status.SUBMITTED
        draft.save(update_fields=["status", "updated_at"])
        record_audit(
            action="report.draft_submitted",
            actor=request.user,
            request=request,
            entity=draft,
            organization_id=draft.organization_id,
            school_id=draft.school_id,
        )
        return Response(ReportDraftSerializer(draft).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        draft = self.get_object()
        if draft.status != ReportDraft.Status.SUBMITTED:
            return Response({"detail": "Only a submitted report may be approved."}, status=409)
        draft.status = ReportDraft.Status.APPROVED
        draft.reviewed_by = request.user
        draft.reviewed_at = timezone.now()
        draft.rejection_reason = ""
        draft.full_clean(exclude=["id"])
        draft.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"]
        )
        record_audit(
            action="report.draft_approved",
            actor=request.user,
            request=request,
            entity=draft,
            organization_id=draft.organization_id,
            school_id=draft.school_id,
        )
        return Response(ReportDraftSerializer(draft).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        draft = self.get_object()
        if draft.status != ReportDraft.Status.SUBMITTED:
            return Response({"detail": "Only a submitted report may be rejected."}, status=409)
        serializer = ReportDraftTransitionSerializer(
            data={"target_status": "rejected", **request.data}
        )
        serializer.is_valid(raise_exception=True)
        draft.status = ReportDraft.Status.REJECTED
        draft.reviewed_by = request.user
        draft.reviewed_at = timezone.now()
        draft.rejection_reason = serializer.validated_data["rejection_reason"]
        draft.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"]
        )
        record_audit(
            action="report.draft_rejected",
            actor=request.user,
            request=request,
            entity=draft,
            organization_id=draft.organization_id,
            school_id=draft.school_id,
        )
        return Response(ReportDraftSerializer(draft).data)

    @action(detail=True, methods=["post"])
    def render(self, request, pk=None):
        draft = self.get_object()
        if draft.status != ReportDraft.Status.APPROVED:
            return Response({"detail": "Only an approved report may be rendered."}, status=409)
        try:
            rendered = render_report_draft(draft.id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        record_audit(
            action="report.draft_rendered",
            actor=request.user,
            request=request,
            entity=rendered,
            organization_id=rendered.organization_id,
            school_id=rendered.school_id,
        )
        return Response(ReportDraftSerializer(rendered).data)
