from celery import shared_task

from hamamooz.apps.organizations.models import ClassSection, Term

from .calculations import recalculate_school_annual, recalculate_school_term


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def recalculate_class_term_task(class_section_id, term_id):
    class_section = ClassSection.objects.get(pk=class_section_id)
    term = Term.objects.get(pk=term_id)
    results = recalculate_school_term(class_section.school, term)
    recalculate_school_annual(class_section.school, term.academic_year)
    target_count = sum(
        result.enrollment.class_section_id == class_section.id for result in results
    )
    return {"calculated": target_count}
