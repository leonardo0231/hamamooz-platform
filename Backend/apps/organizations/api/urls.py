from rest_framework.routers import DefaultRouter

from apps.organizations.api.views import (
    OrganizationViewSet,
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

urlpatterns = router.urls