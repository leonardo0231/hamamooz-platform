from django.db import models


class SystemRole(models.TextChoices):
    ORGANIZATION_MANAGER = (
        "ORGANIZATION_MANAGER",
        "مدیر مجموعه",
    )

    SCHOOL_MANAGER = (
        "SCHOOL_MANAGER",
        "مدیر شعبه",
    )

    ACADEMIC_DEPUTY = (
        "ACADEMIC_DEPUTY",
        "معاون آموزشی",
    )

    OPERATOR = (
        "OPERATOR",
        "اپراتور",
    )

    TEACHER = (
        "TEACHER",
        "دبیر",
    )