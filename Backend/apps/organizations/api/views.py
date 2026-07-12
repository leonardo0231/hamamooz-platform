from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated


from apps.organizations.models import (
    Organization,
    School,
)

from .serializers import (
    OrganizationSerializer,
    SchoolSerializer,
)


class OrganizationViewSet(
    ModelViewSet
):

    permission_classes = [
        IsAuthenticated
    ]

    queryset = Organization.objects.all()

    serializer_class = OrganizationSerializer



class SchoolViewSet(
    ModelViewSet
):

    permission_classes = [
        IsAuthenticated
    ]

    serializer_class = SchoolSerializer


    def get_queryset(self):

        from apps.organizations.selectors import accessible_schools

        return accessible_schools(
            self.request.user
        )