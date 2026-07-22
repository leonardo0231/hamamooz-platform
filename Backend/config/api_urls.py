from django.urls import include, path
from rest_framework.routers import DefaultRouter

from hamamooz.apps.academics.views import (
    AssessmentTypeViewSet,
    AssessmentViewSet,
    CalculationPolicyViewSet,
    CourseOfferingViewSet,
    GradeSubjectViewSet,
    ScoreViewSet,
    SubjectViewSet,
)
from hamamooz.apps.accounts.views import RoleAssignmentViewSet, UserViewSet
from hamamooz.apps.dashboard.views import DashboardSummaryView
from hamamooz.apps.imports.views import ImportJobViewSet
from hamamooz.apps.organizations.views import (
    AcademicYearViewSet,
    ClassSectionViewSet,
    GradeLevelViewSet,
    OrganizationViewSet,
    SchoolViewSet,
    TermViewSet,
)
from hamamooz.apps.reports.views import ReportArchiveViewSet
from hamamooz.apps.students.views import EnrollmentViewSet, GuardianViewSet, StudentViewSet
from hamamooz.apps.attendance.views import (
    AttendanceAlertViewSet,
    AttendancePolicyViewSet,
    AttendanceRecordViewSet,
    AttendanceReportViewSet,
    AttendanceSessionViewSet,
    ParentNotificationViewSet,
)

router = DefaultRouter()
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("schools", SchoolViewSet, basename="school")
router.register("academic-years", AcademicYearViewSet, basename="academic-year")
router.register("terms", TermViewSet, basename="term")
router.register("grade-levels", GradeLevelViewSet, basename="grade-level")
router.register("classes", ClassSectionViewSet, basename="class-section")
router.register("users", UserViewSet, basename="user")
router.register("role-assignments", RoleAssignmentViewSet, basename="role-assignment")
router.register("students", StudentViewSet, basename="student")
router.register("guardians", GuardianViewSet, basename="guardian")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")
router.register("subjects", SubjectViewSet, basename="subject")
router.register("grade-subjects", GradeSubjectViewSet, basename="grade-subject")
router.register("course-offerings", CourseOfferingViewSet, basename="course-offering")
router.register("assessment-types", AssessmentTypeViewSet, basename="assessment-type")
router.register("assessments", AssessmentViewSet, basename="assessment")
router.register("scores", ScoreViewSet, basename="score")
router.register("calculation-policies", CalculationPolicyViewSet, basename="calculation-policy")
router.register(
    "attendance-sessions", AttendanceSessionViewSet, basename="attendance-session"
)
router.register(
    "attendance-records", AttendanceRecordViewSet, basename="attendance-record"
)
router.register(
    "attendance-policies", AttendancePolicyViewSet, basename="attendance-policy"
)
router.register("attendance-alerts", AttendanceAlertViewSet, basename="attendance-alert")
router.register("parent-notifications", ParentNotificationViewSet, basename="parent-notification")
router.register("attendance-reports", AttendanceReportViewSet, basename="attendance-report")
router.register("imports", ImportJobViewSet, basename="import-job")
router.register("reports", ReportArchiveViewSet, basename="report")

urlpatterns = [
    path("auth/", include("hamamooz.apps.accounts.urls")),
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("", include(router.urls)),
]
