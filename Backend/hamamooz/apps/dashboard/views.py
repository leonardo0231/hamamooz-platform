from django.db.models import Avg, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from hamamooz.apps.academics.models import Assessment, CourseOffering, Score, TermResult
from hamamooz.apps.accounts.access import allowed_class_ids, selected_school_ids
from hamamooz.apps.core.models import AuditEvent
from hamamooz.apps.organizations.models import ClassSection
from hamamooz.apps.students.models import Enrollment


class DashboardSummaryView(APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        school_ids = selected_school_ids(request)
        class_ids = allowed_class_ids(request.user, school_ids)
        enrollments = Enrollment.objects.filter(
            school_id__in=school_ids,
            class_section_id__in=class_ids,
            status=Enrollment.Status.ACTIVE,
        )
        classes = ClassSection.objects.filter(id__in=class_ids, is_active=True)
        offerings = CourseOffering.objects.filter(
            class_section_id__in=class_ids,
            class_section__school_id__in=school_ids,
            is_active=True,
        )
        if (
            request.user.role_assignments.filter(role="teacher", is_active=True).exists()
            and not request.user.role_assignments.exclude(role="teacher")
            .filter(is_active=True)
            .exists()
        ):
            offerings = offerings.filter(teacher=request.user)
        assessments = Assessment.objects.filter(course_offering__in=offerings)

        missing_scores = 0
        open_assessments = assessments.filter(
            status__in=[
                Assessment.Status.DRAFT,
                Assessment.Status.SUBMITTED,
                Assessment.Status.REJECTED,
            ]
        ).select_related("course_offering__class_section")
        for assessment in open_assessments:
            expected = Enrollment.objects.filter(
                class_section=assessment.course_offering.class_section,
                status=Enrollment.Status.ACTIVE,
            ).count()
            entered = (
                Score.objects.filter(assessment=assessment)
                .exclude(status=Score.Status.NOT_ENTERED)
                .count()
            )
            missing_scores += max(expected - entered, 0)

        class_averages = list(
            TermResult.objects.filter(enrollment__class_section_id__in=class_ids)
            .values("enrollment__class_section_id", "enrollment__class_section__title")
            .annotate(average=Avg("average"), students=Count("enrollment", distinct=True))
            .order_by("enrollment__class_section__title")
        )
        workflow = {
            item["status"]: item["count"]
            for item in assessments.values("status").annotate(count=Count("id"))
        }
        activities = list(
            AuditEvent.objects.filter(school_id__in=school_ids).values(
                "id", "action", "entity_type", "entity_id", "actor_id", "created_at"
            )[:10]
        )
        by_school = list(
            enrollments.values("school_id", "school__name")
            .annotate(students=Count("student_id", distinct=True))
            .order_by("school__name")
        )
        return Response(
            {
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
