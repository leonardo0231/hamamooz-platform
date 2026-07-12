from django.db import models


class SystemRole(models.TextChoices):
    SYSTEM_ADMIN = (
        "SYSTEM_ADMIN",
        "مدیر کل سامانه",
    )

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