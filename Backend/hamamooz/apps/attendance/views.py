from django.db.models import Prefetch, Q
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from hamamooz.apps.accounts.access import allowed_class_ids, selected_school_ids
from hamamooz.apps.accounts.permissions import RolePermission
from hamamooz.apps.core.viewsets import AuditedModelViewSet
from hamamooz.apps.organizations.models import AcademicYear, ClassSection, School
from hamamooz.apps.students.models import Enrollment

from .models import (
    AttendanceAlert,
    AttendancePolicy,
    AttendanceRecord,
    AttendanceSession,
    ParentNotification,
)
from .permissions import (
    ATTENDANCE_POLICY_MANAGERS,
    ATTENDANCE_REVIEWERS,
    ATTENDANCE_WRITERS,
)
from .selectors import (
    active_enrollments_for_class,
    attendance_date_range,
    enrollment_metrics,
    enrollment_metrics_map,
    report_records,
    scoped_record_queryset,
    scoped_session_queryset,
)
from .serializers import (
    AttendanceAlertSerializer,
    AttendancePolicySerializer,
    AttendanceRecordSerializer,
    AttendanceSessionSerializer,
    BulkAttendanceSerializer,
    ClassAttendanceReportQuerySerializer,
    ClassAttendanceReportResponseSerializer,
    CorrectAttendanceRecordSerializer,
    NotificationChannelsSerializer,
    NotifyGuardiansSerializer,
    ParentNotificationSerializer,
    ReviewAbsenceExcuseSerializer,
    SchoolAttendanceReportQuerySerializer,
    SchoolAttendanceReportResponseSerializer,
    StudentAttendanceReportQuerySerializer,
    StudentAttendanceReportResponseSerializer,
    SubmitAbsenceExcuseSerializer,
)
from .services import (
    acknowledge_alert,
    bulk_record_attendance,
    cancel_attendance_session,
    correct_attendance_record,
    evaluate_policy_alerts,
    finalize_attendance_session,
    queue_record_parent_notifications,
    queue_summary_parent_notifications,
    resolve_alert,
    review_absence_excuse,
    submit_absence_excuse,
)
from .tasks import dispatch_parent_notification


class AttendanceSessionViewSet(AuditedModelViewSet):
    queryset = AttendanceSession.objects.none()
    serializer_class = AttendanceSessionSerializer
    filterset_fields = [
        "school",
        "academic_year",
        "class_section",
        "term",
        "course_offering",
        "session_date",
        "scope",
        "status",
    ]
    search_fields = [
        "title",
        "class_section__title",
        "course_offering__grade_subject__subject__title",
    ]
    ordering_fields = ["session_date", "period_number", "created_at"]
    required_roles_by_action = {
        action_name: ATTENDANCE_WRITERS
        for action_name in [
            "create",
            "update",
            "partial_update",
            "destroy",
            "bulk_mark",
            "finalize",
            "cancel",
        ]
    }

    def get_queryset(self):
        return scoped_session_queryset(self.request).prefetch_related(
            Prefetch(
                "records",
                queryset=AttendanceRecord.objects.select_related("enrollment__student"),
            )
        )

    def perform_create(self, serializer):
        self.perform_audited_create(
            serializer,
            action="attendance.session_created",
            taken_by=self.request.user,
        )

    def perform_update(self, serializer):
        if serializer.instance.status != AttendanceSession.Status.DRAFT:
            raise PermissionDenied("جلسه نهایی‌شده یا لغوشده قابل ویرایش نیست.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.status != AttendanceSession.Status.DRAFT:
            raise PermissionDenied("فقط جلسه پیش‌نویس قابل حذف است.")
        if instance.records.exists():
            raise PermissionDenied("جلسه دارای رکورد باید لغو شود و قابل حذف نیست.")
        super().perform_destroy(instance)

    @action(detail=True, methods=["get"])
    def roster(self, request, pk=None):
        session = self.get_object()
        enrollments = active_enrollments_for_class(session)
        records = {
            record.enrollment_id: record
            for record in AttendanceRecord.objects.filter(session=session).select_related(
                "enrollment__student"
            )
        }
        data = []
        for enrollment in enrollments:
            record = records.get(enrollment.id)
            data.append(
                {
                    "enrollment": str(enrollment.id),
                    "student": str(enrollment.student_id),
                    "student_number": enrollment.student_number,
                    "student_name": enrollment.student.full_name,
                    "record": AttendanceRecordSerializer(record).data if record else None,
                }
            )
        return Response({"session": str(session.id), "count": len(data), "results": data})

    @action(detail=True, methods=["post"], url_path="bulk-mark")
    def bulk_mark(self, request, pk=None):
        session = self.get_object()
        serializer = BulkAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        records = bulk_record_attendance(
            session=session,
            items=serializer.validated_data["records"],
            actor=request.user,
            request=request,
        )
        return Response(
            AttendanceRecordSerializer(records, many=True).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        session = finalize_attendance_session(
            session=self.get_object(), actor=request.user, request=request
        )
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        reason = str(request.data.get("reason", "")).strip()
        if len(reason) < 3:
            return Response(
                {"reason": ["دلیل لغو حداقل سه نویسه باشد."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session = cancel_attendance_session(
            session=self.get_object(),
            actor=request.user,
            reason=reason,
            request=request,
        )
        return Response(self.get_serializer(session).data)


class AttendanceRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AttendanceRecord.objects.none()
    serializer_class = AttendanceRecordSerializer
    permission_classes = [RolePermission]
    filterset_fields = [
        "session",
        "session__school",
        "session__academic_year",
        "session__class_section",
        "session__session_date",
        "session__scope",
        "enrollment",
        "enrollment__student",
        "status",
        "excuse_status",
    ]
    search_fields = [
        "enrollment__student__national_id",
        "enrollment__student__first_name",
        "enrollment__student__last_name",
        "absence_reason",
    ]
    ordering_fields = [
        "session__session_date",
        "late_minutes",
        "early_leave_minutes",
        "updated_at",
    ]
    required_roles_by_action = {
        "correct": ATTENDANCE_WRITERS,
        "submit_excuse": ATTENDANCE_WRITERS,
        "approve_excuse": ATTENDANCE_REVIEWERS,
        "reject_excuse": ATTENDANCE_REVIEWERS,
        "notify_guardians": ATTENDANCE_WRITERS,
    }

    def get_queryset(self):
        return scoped_record_queryset(self.request)

    @action(detail=True, methods=["post"])
    def correct(self, request, pk=None):
        record = self.get_object()
        serializer = CorrectAttendanceRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.pop("reason")
        record = correct_attendance_record(
            record=record,
            data=serializer.validated_data,
            reason=reason,
            actor=request.user,
            request=request,
        )
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=["post"], url_path="submit-excuse")
    def submit_excuse(self, request, pk=None):
        serializer = SubmitAbsenceExcuseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = submit_absence_excuse(
            record=self.get_object(),
            reason=serializer.validated_data["reason"],
            evidence_files=serializer.validated_data["evidence_files"],
            actor=request.user,
            request=request,
        )
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=["post"], url_path="approve-excuse")
    def approve_excuse(self, request, pk=None):
        serializer = ReviewAbsenceExcuseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = review_absence_excuse(
            record=self.get_object(),
            approved=True,
            note=serializer.validated_data["note"],
            actor=request.user,
            request=request,
        )
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=["post"], url_path="reject-excuse")
    def reject_excuse(self, request, pk=None):
        serializer = ReviewAbsenceExcuseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = review_absence_excuse(
            record=self.get_object(),
            approved=False,
            note=serializer.validated_data["note"],
            actor=request.user,
            request=request,
        )
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=["post"], url_path="notify-guardians")
    def notify_guardians(self, request, pk=None):
        serializer = NotificationChannelsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notifications = queue_record_parent_notifications(
            record=self.get_object(),
            channels=serializer.validated_data.get("channels"),
            actor=request.user,
        )
        return Response(
            ParentNotificationSerializer(notifications, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class AttendancePolicyViewSet(AuditedModelViewSet):
    queryset = AttendancePolicy.objects.none()
    serializer_class = AttendancePolicySerializer
    filterset_fields = ["school", "academic_year", "is_active"]
    required_roles_by_action = {
        action_name: ATTENDANCE_POLICY_MANAGERS
        for action_name in ["create", "update", "partial_update", "destroy"]
    }

    def get_queryset(self):
        return AttendancePolicy.objects.filter(
            school_id__in=selected_school_ids(self.request)
        ).select_related("school__organization", "academic_year")


class AttendanceAlertViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AttendanceAlert.objects.none()
    serializer_class = AttendanceAlertSerializer
    permission_classes = [RolePermission]
    filterset_fields = [
        "school",
        "academic_year",
        "enrollment",
        "scope",
        "severity",
        "status",
    ]
    ordering_fields = ["created_at", "absence_count", "absence_percent", "severity"]
    required_roles_by_action = {
        "evaluate": ATTENDANCE_REVIEWERS,
        "acknowledge": ATTENDANCE_REVIEWERS,
        "resolve": ATTENDANCE_REVIEWERS,
    }

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids(self.request.user, school_ids)
        return AttendanceAlert.objects.filter(
            school_id__in=school_ids,
            enrollment__class_section_id__in=class_ids,
        ).select_related(
            "policy",
            "school__organization",
            "academic_year",
            "enrollment__student",
            "enrollment__class_section",
            "acknowledged_by",
            "resolved_by",
        )

    @action(detail=False, methods=["post"])
    def evaluate(self, request):
        policy_id = request.data.get("policy")
        if not policy_id:
            return Response(
                {"policy": ["این فیلد الزامی است."]}, status=status.HTTP_400_BAD_REQUEST
            )
        policy = AttendancePolicy.objects.filter(
            pk=policy_id, school_id__in=selected_school_ids(request)
        ).first()
        if not policy:
            raise PermissionDenied("سیاست حضور و غیاب در محدوده دسترسی شما نیست.")
        alerts = evaluate_policy_alerts(policy=policy, actor=request.user, request=request)
        return Response(self.get_serializer(alerts, many=True).data)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        alert = acknowledge_alert(alert=self.get_object(), actor=request.user, request=request)
        return Response(self.get_serializer(alert).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        alert = resolve_alert(alert=self.get_object(), actor=request.user, request=request)
        return Response(self.get_serializer(alert).data)


class ParentNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ParentNotification.objects.none()
    serializer_class = ParentNotificationSerializer
    permission_classes = [RolePermission]
    filterset_fields = ["school", "student", "guardian", "kind", "channel", "status"]
    ordering_fields = ["created_at", "sent_at", "attempts"]
    required_roles_by_action = {"retry": ATTENDANCE_WRITERS}

    def get_queryset(self):
        school_ids = selected_school_ids(self.request)
        class_ids = allowed_class_ids(self.request.user, school_ids)
        return ParentNotification.objects.filter(
            school_id__in=school_ids,
            enrollment__class_section_id__in=class_ids,
        ).select_related(
            "school__organization",
            "student",
            "enrollment__class_section",
            "guardian",
            "attendance_record",
            "alert",
        )

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        notification = self.get_object()
        if notification.status == ParentNotification.Status.SENT:
            return Response(self.get_serializer(notification).data)
        notification.status = ParentNotification.Status.QUEUED
        notification.next_attempt_at = None
        notification.last_error = ""
        notification.save(update_fields=["status", "next_attempt_at", "last_error", "updated_at"])
        dispatch_parent_notification.delay(str(notification.id))
        return Response(self.get_serializer(notification).data, status=202)


class AttendanceReportViewSet(viewsets.GenericViewSet):
    queryset = AttendanceRecord.objects.none()
    serializer_class = StudentAttendanceReportResponseSerializer
    permission_classes = [RolePermission]
    pagination_class = None
    filter_backends = []
    required_roles_by_action = {"notify_guardians": ATTENDANCE_WRITERS}
    serializer_classes = {
        "student": StudentAttendanceReportResponseSerializer,
        "classroom": ClassAttendanceReportResponseSerializer,
        "school": SchoolAttendanceReportResponseSerializer,
        "notify_guardians": NotifyGuardiansSerializer,
    }

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_class)

    def _validate_enrollment_scope(self, request, enrollment):
        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids(request.user, school_ids)
        if enrollment.school_id not in set(school_ids) or enrollment.class_section_id not in set(
            class_ids
        ):
            raise PermissionDenied("ثبت‌نام در محدوده دسترسی شما نیست.")

    @extend_schema(
        parameters=[StudentAttendanceReportQuerySerializer],
        responses={200: StudentAttendanceReportResponseSerializer},
    )
    @action(detail=False, methods=["get"])
    def student(self, request):
        serializer = StudentAttendanceReportQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        enrollment = serializer.validated_data["enrollment"]
        self._validate_enrollment_scope(request, enrollment)
        date_from, date_to = attendance_date_range(
            academic_year=enrollment.academic_year,
            date_from=serializer.validated_data.get("date_from"),
            date_to=serializer.validated_data.get("date_to"),
        )
        scope = serializer.validated_data.get("scope")
        metrics = enrollment_metrics(
            enrollment=enrollment,
            date_from=date_from,
            date_to=date_to,
            scope=scope,
            include_excused=True,
        )
        records = (
            report_records(date_from=date_from, date_to=date_to, scope=scope)
            .filter(enrollment=enrollment)
            .select_related(
                "session__class_section",
                "session__course_offering__grade_subject__subject",
                "enrollment__student",
            )
        )
        return Response(
            {
                "student": {
                    "id": str(enrollment.student_id),
                    "name": enrollment.student.full_name,
                    "enrollment": str(enrollment.id),
                    "student_number": enrollment.student_number,
                    "class_section": str(enrollment.class_section_id),
                    "class_title": enrollment.class_section.title,
                },
                "date_from": date_from,
                "date_to": date_to,
                "scope": scope,
                "metrics": metrics,
                "records": AttendanceRecordSerializer(records, many=True).data,
            }
        )

    @extend_schema(
        parameters=[ClassAttendanceReportQuerySerializer],
        responses={200: ClassAttendanceReportResponseSerializer},
    )
    @action(detail=False, methods=["get"], url_path="class")
    def classroom(self, request):
        serializer = ClassAttendanceReportQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids(request.user, school_ids)
        class_section = (
            ClassSection.objects.filter(
                pk=serializer.validated_data["class_section"], id__in=class_ids
            )
            .select_related("school__organization", "academic_year", "grade_level")
            .first()
        )
        if not class_section:
            raise PermissionDenied("کلاس در محدوده دسترسی شما نیست.")
        requested_year_id = serializer.validated_data.get("academic_year")
        if requested_year_id and requested_year_id != class_section.academic_year_id:
            raise ValidationError({"academic_year": "سال تحصیلی با کلاس انتخاب‌شده سازگار نیست."})
        date_from, date_to = attendance_date_range(
            academic_year=class_section.academic_year,
            date_from=serializer.validated_data.get("date_from"),
            date_to=serializer.validated_data.get("date_to"),
        )
        scope = serializer.validated_data.get("scope")
        enrollments = (
            Enrollment.all_objects.filter(
                class_section=class_section,
                academic_year=class_section.academic_year,
                enrolled_on__lte=date_to,
                is_deleted=False,
            )
            .filter(Q(left_on__isnull=True) | Q(left_on__gte=date_from))
            .select_related("student", "class_section")
        )
        enrollment_list = list(enrollments)
        metrics_map = enrollment_metrics_map(
            enrollment_ids=[enrollment.id for enrollment in enrollment_list],
            date_from=date_from,
            date_to=date_to,
            scope=scope,
            include_excused=True,
        )
        students = []
        total_absences = 0
        total_sessions = 0
        for enrollment in enrollment_list:
            metrics = metrics_map[enrollment.id]
            total_absences += metrics["absence_count"]
            total_sessions += metrics["total_sessions"]
            students.append(
                {
                    "enrollment": str(enrollment.id),
                    "student": str(enrollment.student_id),
                    "student_name": enrollment.student.full_name,
                    "student_number": enrollment.student_number,
                    **metrics,
                }
            )
        overall_percent = 0
        if total_sessions:
            overall_percent = round(total_absences * 100 / total_sessions, 2)
        return Response(
            {
                "class_section": {
                    "id": str(class_section.id),
                    "title": class_section.title,
                    "school_name": class_section.school.name,
                    "organization_name": class_section.school.organization.name,
                },
                "date_from": date_from,
                "date_to": date_to,
                "scope": scope,
                "summary": {
                    "student_count": len(students),
                    "total_attendance_records": total_sessions,
                    "total_absences": total_absences,
                    "absence_percent": overall_percent,
                },
                "students": students,
            }
        )

    @extend_schema(
        parameters=[SchoolAttendanceReportQuerySerializer],
        responses={200: SchoolAttendanceReportResponseSerializer},
    )
    @action(detail=False, methods=["get"])
    def school(self, request):
        serializer = SchoolAttendanceReportQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        school = (
            School.objects.filter(
                pk=serializer.validated_data["school"], id__in=selected_school_ids(request)
            )
            .select_related("organization")
            .first()
        )
        if not school:
            raise PermissionDenied("شعبه در محدوده دسترسی شما نیست.")
        year = AcademicYear.objects.filter(
            pk=serializer.validated_data["academic_year"],
            organization=school.organization,
        ).first()
        if not year:
            raise PermissionDenied("سال تحصیلی با شعبه انتخاب‌شده سازگار نیست.")
        date_from, date_to = attendance_date_range(
            academic_year=year,
            date_from=serializer.validated_data.get("date_from"),
            date_to=serializer.validated_data.get("date_to"),
        )
        scope = serializer.validated_data.get("scope")
        class_ids = allowed_class_ids(request.user, [school.id])
        classes = ClassSection.objects.filter(
            school=school, academic_year=year, id__in=class_ids
        ).select_related("grade_level")
        class_list = list(classes)
        enrollment_list = list(
            Enrollment.all_objects.filter(
                class_section__in=class_list,
                academic_year=year,
                enrolled_on__lte=date_to,
                is_deleted=False,
            )
            .filter(Q(left_on__isnull=True) | Q(left_on__gte=date_from))
            .select_related("student", "class_section")
        )
        metrics_map = enrollment_metrics_map(
            enrollment_ids=[enrollment.id for enrollment in enrollment_list],
            date_from=date_from,
            date_to=date_to,
            scope=scope,
            include_excused=True,
        )
        enrollments_by_class = {class_section.id: [] for class_section in class_list}
        for enrollment in enrollment_list:
            enrollments_by_class[enrollment.class_section_id].append(enrollment)

        class_results = []
        school_total = 0
        school_absent = 0
        for class_section in class_list:
            class_enrollments = enrollments_by_class[class_section.id]
            class_total = sum(
                metrics_map[enrollment.id]["total_sessions"] for enrollment in class_enrollments
            )
            class_absent = sum(
                metrics_map[enrollment.id]["absence_count"] for enrollment in class_enrollments
            )
            school_total += class_total
            school_absent += class_absent
            class_results.append(
                {
                    "class_section": str(class_section.id),
                    "class_title": class_section.title,
                    "grade_title": class_section.grade_level.title,
                    "student_count": len(class_enrollments),
                    "total_attendance_records": class_total,
                    "absence_count": class_absent,
                    "absence_percent": round(class_absent * 100 / class_total, 2)
                    if class_total
                    else 0,
                }
            )
        return Response(
            {
                "school": {
                    "name": school.name,
                    "organization_name": school.organization.name,
                },
                "academic_year": {"id": str(year.id), "title": year.title},
                "date_from": date_from,
                "date_to": date_to,
                "scope": scope,
                "summary": {
                    "class_count": len(class_results),
                    "total_attendance_records": school_total,
                    "absence_count": school_absent,
                    "absence_percent": round(school_absent * 100 / school_total, 2)
                    if school_total
                    else 0,
                },
                "classes": class_results,
            }
        )

    @extend_schema(
        request=NotifyGuardiansSerializer,
        responses={201: ParentNotificationSerializer(many=True)},
    )
    @action(detail=False, methods=["post"], url_path="notify-guardians")
    def notify_guardians(self, request):
        serializer = NotifyGuardiansSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enrollment = serializer.validated_data["enrollment"]
        self._validate_enrollment_scope(request, enrollment)
        date_from, date_to = attendance_date_range(
            academic_year=enrollment.academic_year,
            date_from=serializer.validated_data.get("date_from"),
            date_to=serializer.validated_data.get("date_to"),
        )
        notifications = queue_summary_parent_notifications(
            enrollment=enrollment,
            date_from=date_from,
            date_to=date_to,
            scope=serializer.validated_data.get("scope"),
            channels=serializer.validated_data.get("channels"),
            actor=request.user,
        )
        return Response(
            ParentNotificationSerializer(notifications, many=True).data,
            status=status.HTTP_201_CREATED,
        )
