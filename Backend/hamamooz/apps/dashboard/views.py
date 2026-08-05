from collections import defaultdict

from django.db.models import Avg, Count, F, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from hamamooz.apps.academics.models import Assessment, CourseOffering, Score, TermResult
from hamamooz.apps.accounts.access import (
    allowed_class_ids,
    broad_access_school_ids,
    selected_school_ids,
)
from hamamooz.apps.core.models import AuditEvent
from hamamooz.apps.organizations.models import ClassSection, Term
from hamamooz.apps.students.models import Enrollment

from .serializers import DashboardSummarySerializer


class DashboardSummaryView(APIView):
    @extend_schema(responses={200: DashboardSummarySerializer})
    def get(self, request):
        school_ids = selected_school_ids(request)
        term_id = request.query_params.get("term")
        term_queryset = (
            Term.objects.select_related("academic_year")
            .filter(academic_year__organization__schools__id__in=school_ids)
            .distinct()
        )
        if term_id:
            try:
                term = term_queryset.get(pk=term_id)
            except (Term.DoesNotExist, ValueError, TypeError) as exc:
                raise ValidationError({"term": "نوبت انتخاب‌شده معتبر نیست."}) from exc
        else:
            today = timezone.localdate()
            term = (
                term_queryset.filter(starts_on__lte=today, ends_on__gte=today)
                .order_by("starts_on")
                .first()
                or term_queryset.filter(academic_year__is_current=True)
                .order_by("starts_on")
                .first()
            )
            if term is None:
                raise ValidationError({"term": "برای شعبه انتخاب‌شده نوبت فعالی تعریف نشده است."})
        class_ids = allowed_class_ids(request.user, school_ids)
        broad_school_ids = broad_access_school_ids(request.user, school_ids)
        enrollments = Enrollment.objects.filter(
            school_id__in=school_ids,
            class_section_id__in=class_ids,
            status=Enrollment.Status.ACTIVE,
        )
        classes = ClassSection.objects.filter(id__in=class_ids, is_active=True)
        offerings = CourseOffering.objects.filter(
            class_section_id__in=class_ids,
            class_section__school_id__in=school_ids,
            term=term,
            is_active=True,
        ).filter(Q(class_section__school_id__in=broad_school_ids) | Q(teacher=request.user))
        assessments = Assessment.objects.filter(course_offering__in=offerings)

        open_assessments = assessments.filter(
            status__in=[
                Assessment.Status.DRAFT,
                Assessment.Status.SUBMITTED,
                Assessment.Status.REJECTED,
            ]
        ).values("id", "course_offering__class_section_id")
        assessment_rows = list(open_assessments)
        active_by_class = defaultdict(set)
        for class_id, enrollment_id in Enrollment.objects.filter(
            class_section_id__in=class_ids,
            status=Enrollment.Status.ACTIVE,
        ).values_list("class_section_id", "id"):
            active_by_class[class_id].add(enrollment_id)
        entered_by_assessment = defaultdict(set)
        for assessment_id, enrollment_id in (
            Score.objects.filter(assessment_id__in=[row["id"] for row in assessment_rows])
            .exclude(status=Score.Status.NOT_ENTERED)
            .values_list("assessment_id", "enrollment_id")
        ):
            entered_by_assessment[assessment_id].add(enrollment_id)
        missing_scores = sum(
            len(
                active_by_class[row["course_offering__class_section_id"]]
                - entered_by_assessment[row["id"]]
            )
            for row in assessment_rows
        )

        class_averages = list(
            TermResult.objects.filter(
                enrollment__class_section_id__in=class_ids,
                term=term,
                average__isnull=False,
            )
            .values("enrollment__class_section_id", "enrollment__class_section__title")
            .annotate(average=Avg("average"), students=Count("enrollment", distinct=True))
            .order_by("enrollment__class_section__title")
        )
        workflow = {
            item["status"]: item["count"]
            for item in assessments.values("status").annotate(count=Count("id"))
        }
        activities = list(
            AuditEvent.objects.filter(
                Q(school_id__in=broad_school_ids) | Q(school_id__in=school_ids, actor=request.user)
            ).values("id", "action", "entity_type", "entity_id", "actor_id", "created_at")[:10]
        )
        by_school = list(
            enrollments.values(
                school_name=F("school__name"),
                organization_name=F("school__organization__name"),
            )
            .annotate(students=Count("student_id", distinct=True))
            .order_by("organization_name", "school_name")
        )
        return Response(
            {
                "selected_term": {
                    "id": str(term.id),
                    "title": term.title,
                },
                "counts": {
                    "students": enrollments.values("student_id").distinct().count(),
                    "classes": classes.count(),
                    "teachers": offerings.values("teacher_id").distinct().count(),
                    "missing_scores": missing_scores,
                },
                "students_by_school": by_school,
                "class_averages": class_averages,
                "assessment_workflow": workflow,
                "latest_activities": activities,
                "quick_links": {
                    "score_entry": "/api/v1/assessments/",
                    "report_cards": "/api/v1/reports/",
                    "imports": "/api/v1/imports/",
                },
            }
        )
