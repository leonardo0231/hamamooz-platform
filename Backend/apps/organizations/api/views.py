from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import (
    mixins,
    serializers,
    status,
)
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import (
    GenericViewSet,
    ModelViewSet,
)

from apps.organizations.api.exceptions import (
    OrganizationAccessDenied,
    SchoolAccessDenied,
)
from apps.organizations.api.permissions import (
    OrganizationAccessPermission,
    SchoolAccessPermission,
)
from apps.organizations.api.serializers import (
    MembershipActivateSerializer,
    MembershipDeactivateSerializer,
    OrganizationSerializer,
    RoleAssignmentSerializer,
    RoleGrantSerializer,
    RoleRevokeSerializer,
    SchoolMembershipCreateSerializer,
    SchoolMembershipSerializer,
    SchoolSerializer,
)
from apps.organizations.policies import (
    can_create_school_in_organization,
    can_manage_school,
)
from apps.organizations.selectors import (
    accessible_memberships,
    accessible_organizations,
    accessible_schools,
)
from apps.organizations.services import (
    AccessDeniedError,
    AccessServiceError,
    AccessValidationError,
    activate_membership,
    create_membership,
    deactivate_membership,
    grant_role,
    revoke_role,
)


def _raise_service_error(
    exc: AccessServiceError,
) -> None:
    if isinstance(exc, AccessDeniedError):
        raise SchoolAccessDenied(
            str(exc)
        ) from exc

    if isinstance(exc, AccessValidationError):
        raise serializers.ValidationError(
            {
                "detail": str(exc),
            }
        ) from exc

    raise exc


class OrganizationViewSet(ModelViewSet):
    serializer_class = OrganizationSerializer

    permission_classes = (
        IsAuthenticated,
        OrganizationAccessPermission,
    )

    http_method_names = (
        "get",
        "post",
        "patch",
        "head",
        "options",
    )

    search_fields = (
        "name",
        "code",
    )

    ordering_fields = (
        "name",
        "code",
        "created_at",
    )

    filterset_fields = (
        "is_active",
    )

    def get_queryset(self):
        return accessible_organizations(
            self.request.user
        ).order_by("name")

    def perform_update(
        self,
        serializer: OrganizationSerializer,
    ) -> None:
        if not self.request.user.is_superuser:
            allowed_fields = {"name"}

            submitted_fields = set(
                serializer.validated_data
            )

            if submitted_fields - allowed_fields:
                raise OrganizationAccessDenied(
                    "Organization managers may only "
                    "edit the organization name."
                )

        serializer.save()


class SchoolViewSet(ModelViewSet):
    serializer_class = SchoolSerializer

    permission_classes = (
        IsAuthenticated,
        SchoolAccessPermission,
    )

    http_method_names = (
        "get",
        "post",
        "patch",
        "head",
        "options",
    )

    search_fields = (
        "name",
        "code",
        "organization__name",
    )

    ordering_fields = (
        "name",
        "code",
        "created_at",
    )

    filterset_fields = (
        "organization",
        "is_active",
    )

    def get_queryset(self):
        return (
            accessible_schools(
                self.request.user
            )
            .select_related("organization")
            .order_by(
                "organization__name",
                "name",
            )
        )

    def perform_create(
        self,
        serializer: SchoolSerializer,
    ) -> None:
        organization = (
            serializer.validated_data[
                "organization"
            ]
        )

        if not can_create_school_in_organization(
            self.request.user,
            organization,
        ):
            raise SchoolAccessDenied(
                "Only system administrators and "
                "organization managers may create "
                "schools."
            )

        serializer.save()

    def perform_update(
        self,
        serializer: SchoolSerializer,
    ) -> None:
        school = serializer.instance
        user = self.request.user

        if not can_manage_school(
            user,
            school,
        ):
            raise SchoolAccessDenied(
                "You are not allowed to update "
                "this school."
            )

        if not user.is_superuser:
            allowed_fields = {
                "name",
                "code",
                "is_active",
            }

            submitted_fields = set(
                serializer.validated_data
            )

            if submitted_fields - allowed_fields:
                raise SchoolAccessDenied(
                    "You are not allowed to modify "
                    "one or more submitted fields."
                )

        serializer.save()


class SchoolMembershipViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    permission_classes = (IsAuthenticated,)

    http_method_names = (
        "get",
        "post",
        "head",
        "options",
    )

    filterset_fields = (
        "school",
        "user",
        "is_active",
    )

    search_fields = (
        "user__email",
        "school__name",
        "school__code",
    )

    ordering_fields = (
        "created_at",
        "updated_at",
        "user__email",
    )

    def get_queryset(self):
        return accessible_memberships(
            self.request.user
        ).order_by(
            "school__name",
            "user__email",
        )

    def get_serializer_class(self):
        serializers_by_action = {
            "create": (
                SchoolMembershipCreateSerializer
            ),
            "activate": (
                MembershipActivateSerializer
            ),
            "deactivate": (
                MembershipDeactivateSerializer
            ),
            "grant_role_action": (
                RoleGrantSerializer
            ),
            "revoke_role_action": (
                RoleRevokeSerializer
            ),
        }

        return serializers_by_action.get(
            self.action,
            SchoolMembershipSerializer,
        )

    @extend_schema(
        request=SchoolMembershipCreateSerializer,
        responses={
            201: SchoolMembershipSerializer,
        },
    )
    def create(
        self,
        request: Request,
        *args,
        **kwargs,
    ) -> Response:
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            membership = create_membership(
                user=serializer.validated_data[
                    "user"
                ],
                school=serializer.validated_data[
                    "school"
                ],
                actor=request.user,
                reason=serializer.validated_data.get(
                    "reason",
                    "",
                ),
            )
        except AccessServiceError as exc:
            _raise_service_error(exc)

        output = SchoolMembershipSerializer(
            membership,
            context=self.get_serializer_context(),
        )

        return Response(
            output.data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=MembershipActivateSerializer,
        responses={
            200: SchoolMembershipSerializer,
        },
    )
    @action(
        detail=True,
        methods=("post",),
        url_path="activate",
    )
    def activate(
        self,
        request: Request,
        pk=None,
    ) -> Response:
        membership = self.get_object()

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            membership = activate_membership(
                membership=membership,
                actor=request.user,
                reason=serializer.validated_data.get(
                    "reason",
                    "",
                ),
            )
        except AccessServiceError as exc:
            _raise_service_error(exc)

        output = SchoolMembershipSerializer(
            membership,
            context=self.get_serializer_context(),
        )

        return Response(output.data)

    @extend_schema(
        request=MembershipDeactivateSerializer,
        responses={
            200: SchoolMembershipSerializer,
        },
    )
    @action(
        detail=True,
        methods=("post",),
        url_path="deactivate",
    )
    def deactivate(
        self,
        request: Request,
        pk=None,
    ) -> Response:
        membership = self.get_object()

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            membership = deactivate_membership(
                membership=membership,
                actor=request.user,
                reason=serializer.validated_data[
                    "reason"
                ],
            )
        except AccessServiceError as exc:
            _raise_service_error(exc)

        output = SchoolMembershipSerializer(
            membership,
            context=self.get_serializer_context(),
        )

        return Response(output.data)

    @extend_schema(
        request=RoleGrantSerializer,
        responses={
            200: RoleAssignmentSerializer,
        },
    )
    @action(
        detail=True,
        methods=("post",),
        url_path="grant-role",
        url_name="grant-role",
    )
    def grant_role_action(
        self,
        request: Request,
        pk=None,
    ) -> Response:
        membership = self.get_object()

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            assignment = grant_role(
                membership=membership,
                actor=request.user,
                role=serializer.validated_data[
                    "role"
                ],
                reason=serializer.validated_data.get(
                    "reason",
                    "",
                ),
            )
        except AccessServiceError as exc:
            _raise_service_error(exc)

        output = RoleAssignmentSerializer(
            assignment
        )

        return Response(output.data)

    @extend_schema(
        request=RoleRevokeSerializer,
        responses={
            200: RoleAssignmentSerializer,
        },
    )
    @action(
        detail=True,
        methods=("post",),
        url_path="revoke-role",
        url_name="revoke-role",
    )
    def revoke_role_action(
        self,
        request: Request,
        pk=None,
    ) -> Response:
        membership = self.get_object()

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            assignment = revoke_role(
                membership=membership,
                actor=request.user,
                role=serializer.validated_data[
                    "role"
                ],
                reason=serializer.validated_data[
                    "reason"
                ],
            )
        except AccessServiceError as exc:
            _raise_service_error(exc)

        output = RoleAssignmentSerializer(
            assignment
        )

        return Response(output.data)