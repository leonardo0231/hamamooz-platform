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
from hamamooz.apps.activities.views import (
    ActivityAchievementViewSet,
    ActivityAttachmentViewSet,
    ActivityParticipationViewSet,
    ActivityViewSet,
)
from hamamooz.apps.analytics.views import (
    AnalyticsRuleConfigViewSet,
    AnalyticsRunViewSet,
    OperationalAlertViewSet,
    StudentRiskSignalViewSet,
)
from hamamooz.apps.attendance.views import (
    AttendanceAlertViewSet,
    AttendancePolicyViewSet,
    AttendanceRecordViewSet,
    AttendanceReportViewSet,
    AttendanceSessionViewSet,
    ParentNotificationViewSet,
)
from hamamooz.apps.behavior.views import (
    BehaviorActionViewSet,
    BehaviorAttachmentViewSet,
    BehaviorEventTypeViewSet,
    BehaviorEventViewSet,
    BehaviorFollowUpViewSet,
)
from hamamooz.apps.counseling.views import (
    CounselingActionPlanViewSet,
    CounselingCaseViewSet,
    CounselingFollowUpViewSet,
    CounselingReferralViewSet,
)
from hamamooz.apps.dashboard.views import (
    CounselorDashboardView,
    DashboardSummaryView,
    EducationalDashboardView,
    GuideTeacherDashboardView,
    ManagerDashboardView,
    StudentAffairsDashboardView,
    TeacherDashboardView,
)
from hamamooz.apps.evaluations.views import MonthlyEvaluationViewSet
from hamamooz.apps.guidance.views import (
    GuideActionPlanViewSet,
    GuideFollowUpViewSet,
    GuideTeacherAssignmentViewSet,
)
from hamamooz.apps.imports.views import ImportJobViewSet
from hamamooz.apps.organizations.views import (
    AcademicYearViewSet,
    ClassSectionViewSet,
    GradeLevelViewSet,
    OrganizationViewSet,
    SchoolViewSet,
    TermViewSet,
)
from hamamooz.apps.portal.views import (
    ParentChildAttendanceView,
    ParentChildGuidePlansView,
    ParentChildRecommendationsView,
    ParentChildrenView,
    ParentChildReportDownloadView,
    ParentChildReportsView,
    PortalVisibilityPolicyViewSet,
    StudentAttendanceView,
    StudentGuidePlansView,
    StudentRecommendationsView,
    StudentReportDownloadView,
    StudentReportsView,
)
from hamamooz.apps.recommendations.views import RecommendationViewSet
from hamamooz.apps.reports.views import (
    ReportArchiveViewSet,
    ReportBatchViewSet,
    ReportDraftViewSet,
    ReportTemplateViewSet,
)
from hamamooz.apps.students.views import EnrollmentViewSet, GuardianViewSet, StudentViewSet

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
router.register("attendance-sessions", AttendanceSessionViewSet, basename="attendance-session")
router.register("attendance-records", AttendanceRecordViewSet, basename="attendance-record")
router.register("attendance-policies", AttendancePolicyViewSet, basename="attendance-policy")
router.register("attendance-alerts", AttendanceAlertViewSet, basename="attendance-alert")
router.register("parent-notifications", ParentNotificationViewSet, basename="parent-notification")
router.register("attendance-reports", AttendanceReportViewSet, basename="attendance-report")
router.register("behavior-event-types", BehaviorEventTypeViewSet, basename="behavior-event-type")
router.register("behavior-events", BehaviorEventViewSet, basename="behavior-event")
router.register("behavior-actions", BehaviorActionViewSet, basename="behavior-action")
router.register("behavior-follow-ups", BehaviorFollowUpViewSet, basename="behavior-follow-up")
router.register("behavior-attachments", BehaviorAttachmentViewSet, basename="behavior-attachment")
router.register("activities", ActivityViewSet, basename="activity")
router.register(
    "activity-participations", ActivityParticipationViewSet, basename="activity-participation"
)
router.register(
    "activity-achievements", ActivityAchievementViewSet, basename="activity-achievement"
)
router.register("activity-attachments", ActivityAttachmentViewSet, basename="activity-attachment")
router.register(
    "guide-teacher-assignments", GuideTeacherAssignmentViewSet, basename="guide-teacher-assignment"
)
router.register("guide-follow-ups", GuideFollowUpViewSet, basename="guide-follow-up")
router.register("guide-action-plans", GuideActionPlanViewSet, basename="guide-action-plan")
router.register("counseling/cases", CounselingCaseViewSet, basename="counseling-case")
router.register("counseling/follow-ups", CounselingFollowUpViewSet, basename="counseling-follow-up")
router.register(
    "counseling/action-plans", CounselingActionPlanViewSet, basename="counseling-action-plan"
)
router.register("counseling/referrals", CounselingReferralViewSet, basename="counseling-referral")
router.register(
    "analytics/rule-configs", AnalyticsRuleConfigViewSet, basename="analytics-rule-config"
)
router.register("analytics/runs", AnalyticsRunViewSet, basename="analytics-run")
router.register("analytics/risk-signals", StudentRiskSignalViewSet, basename="risk-signal")
router.register(
    "analytics/operational-alerts", OperationalAlertViewSet, basename="operational-alert"
)
router.register("recommendations", RecommendationViewSet, basename="recommendation")
router.register("reports/templates", ReportTemplateViewSet, basename="report-template")
router.register("reports/drafts", ReportDraftViewSet, basename="report-draft")
router.register(
    "portal/visibility-policies", PortalVisibilityPolicyViewSet, basename="portal-visibility-policy"
)
router.register("imports", ImportJobViewSet, basename="import-job")
router.register(
    "monthly-evaluations",
    MonthlyEvaluationViewSet,
    basename="monthly-evaluation",
)
router.register("reports/batches", ReportBatchViewSet, basename="report-batch")
router.register("reports", ReportArchiveViewSet, basename="report")

urlpatterns = [
    path("auth/", include("hamamooz.apps.accounts.urls")),
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("dashboard/manager/", ManagerDashboardView.as_view(), name="dashboard-manager"),
    path(
        "dashboard/educational/", EducationalDashboardView.as_view(), name="dashboard-educational"
    ),
    path(
        "dashboard/student-affairs/",
        StudentAffairsDashboardView.as_view(),
        name="dashboard-student-affairs",
    ),
    path("dashboard/counselor/", CounselorDashboardView.as_view(), name="dashboard-counselor"),
    path(
        "dashboard/guide-teacher/",
        GuideTeacherDashboardView.as_view(),
        name="dashboard-guide-teacher",
    ),
    path("dashboard/teacher/", TeacherDashboardView.as_view(), name="dashboard-teacher"),
    path("portal/me/children/", ParentChildrenView.as_view(), name="portal-parent-children"),
    path(
        "portal/children/<uuid:student_id>/reports/",
        ParentChildReportsView.as_view(),
        name="portal-parent-child-reports",
    ),
    path(
        "portal/children/<uuid:student_id>/reports/<uuid:report_id>/download/",
        ParentChildReportDownloadView.as_view(),
        name="portal-parent-child-report-download",
    ),
    path(
        "portal/children/<uuid:student_id>/recommendations/",
        ParentChildRecommendationsView.as_view(),
        name="portal-parent-child-recommendations",
    ),
    path(
        "portal/children/<uuid:student_id>/attendance/",
        ParentChildAttendanceView.as_view(),
        name="portal-parent-child-attendance",
    ),
    path(
        "portal/children/<uuid:student_id>/guide-plans/",
        ParentChildGuidePlansView.as_view(),
        name="portal-parent-child-guide-plans",
    ),
    path("portal/student/reports/", StudentReportsView.as_view(), name="portal-student-reports"),
    path(
        "portal/student/reports/<uuid:report_id>/download/",
        StudentReportDownloadView.as_view(),
        name="portal-student-report-download",
    ),
    path(
        "portal/student/recommendations/",
        StudentRecommendationsView.as_view(),
        name="portal-student-recommendations",
    ),
    path(
        "portal/student/attendance/",
        StudentAttendanceView.as_view(),
        name="portal-student-attendance",
    ),
    path(
        "portal/student/guide-plans/",
        StudentGuidePlansView.as_view(),
        name="portal-student-guide-plans",
    ),
    path("", include(router.urls)),
]
