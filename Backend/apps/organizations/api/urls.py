from rest_framework.routers import DefaultRouter

from apps.organizations.api.views import (
    OrganizationViewSet,
    SchoolMembershipViewSet,
    SchoolViewSet,
)

router = DefaultRouter()

router.register(
    "organizations",
    OrganizationViewSet,
    basename="organization",
)

router.register(
    "schools",
    SchoolViewSet,
    basename="school",
)

router.register(
    "memberships",
    SchoolMembershipViewSet,
    basename="membership",
)

urlpatterns = router.urls