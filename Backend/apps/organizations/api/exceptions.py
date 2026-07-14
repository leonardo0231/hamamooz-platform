from rest_framework.exceptions import PermissionDenied


class OrganizationAccessDenied(PermissionDenied):
    default_detail = "You do not have permission to manage this organization."
    default_code = "organization_access_denied"


class SchoolAccessDenied(PermissionDenied):
    default_detail = "You do not have permission to manage this school."
    default_code = "school_access_denied"
