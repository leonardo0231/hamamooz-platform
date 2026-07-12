from django.conf import settings
from django.db import models


from apps.permissions.models import SystemRole


class Organization(models.Model):
    name = models.CharField(
        max_length=200
    )

    code = models.CharField(
        max_length=50,
        unique=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


    class Meta:
        ordering = [
            "name"
        ]


    def __str__(self):
        return self.name



class School(models.Model):

    organization = models.ForeignKey(
        Organization,
        related_name="schools",
        on_delete=models.CASCADE
    )

    name = models.CharField(
        max_length=200
    )

    code = models.CharField(
        max_length=50
    )

    is_active = models.BooleanField(
        default=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "code"
                ],
                name="unique_school_code_per_org"
            )
        ]


    def __str__(self):
        return self.name
    

class SchoolMembership(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="school_memberships",
        on_delete=models.CASCADE
    )


    school = models.ForeignKey(
        School,
        related_name="memberships",
        on_delete=models.CASCADE
    )


    is_active = models.BooleanField(
        default=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "school"
                ],
                name="unique_user_school_membership"
            )
        ]

    
class RoleAssignment(models.Model):

    membership = models.ForeignKey(
        SchoolMembership,
        related_name="roles",
        on_delete=models.CASCADE
    )


    role = models.CharField(
        max_length=50,
        choices=SystemRole.choices
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "membership",
                    "role"
                ],
                name="unique_role_assignment"
            )
        ]