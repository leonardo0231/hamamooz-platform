def accessible_schools(user):

    if user.is_superuser:
        from .models import School
        return School.objects.all()


    return School.objects.filter(
        memberships__user=user,
        memberships__is_active=True
    ).distinct()