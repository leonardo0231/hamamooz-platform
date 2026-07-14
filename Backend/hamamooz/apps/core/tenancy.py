def first_attr(obj, paths):
    for path in paths:
        current = obj
        try:
            for part in path.split("."):
                current = getattr(current, part)
            if current is not None:
                return current
        except (AttributeError, TypeError):
            continue
    return None


def object_school_id(obj):
    value = first_attr(
        obj,
        [
            "school_id",
            "class_section.school_id",
            "enrollment.school_id",
            "course_offering.class_section.school_id",
            "assessment.course_offering.class_section.school_id",
            "score.enrollment.school_id",
        ],
    )
    return value


def object_organization_id(obj):
    value = first_attr(
        obj,
        [
            "organization_id",
            "school.organization_id",
            "academic_year.organization_id",
            "grade_level.organization_id",
            "class_section.school.organization_id",
            "student.organization_id",
            "enrollment.student.organization_id",
            "subject.organization_id",
            "grade_subject.subject.organization_id",
            "course_offering.class_section.school.organization_id",
            "assessment.course_offering.class_section.school.organization_id",
        ],
    )
    return value
