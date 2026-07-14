from rest_framework import serializers

from apps.organizations.models import (
    Organization,
    School,
)


class OrganizationSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = Organization

        fields = [
            "id",
            "name",
            "code",
            "is_active",
        ]



class SchoolSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = School

        fields = [
            "id",
            "organization",
            "name",
            "code",
            "is_active",
        ]