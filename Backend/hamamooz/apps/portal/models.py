from django.db import models

from hamamooz.apps.core.models import SoftDeleteModel


class PortalVisibilityPolicy(SoftDeleteModel):
    class Resource(models.TextChoices):
        REPORT_CARD = "report_card", "Report card"
        RECOMMENDATIONS = "recommendations", "Recommendations"
        ATTENDANCE_SUMMARY = "attendance_summary", "Attendance summary"
        BEHAVIOR = "behavior", "Behavior"
        COUNSELING = "counseling", "Counseling"
        GUIDE_PLAN = "guide_plan", "Guide plan"

    class Visibility(models.TextChoices):
        RELEASED = "released", "Released only"
        APPROVED_ONLY = "approved_only", "Approved only"
        VISIBLE = "visible", "Visible"
        HIDDEN = "hidden", "Hidden"
        NEVER = "never", "Never"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="portal_visibility_policies",
    )
    resource = models.CharField(max_length=40, choices=Resource.choices)
    visibility = models.CharField(max_length=30, choices=Visibility.choices)

    class Meta:
        ordering = ["organization", "resource"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "resource"],
                condition=models.Q(is_deleted=False),
                name="uq_portal_visibility_org_resource",
            )
        ]
