from celery import shared_task

from hamamooz.apps.organizations.models import ClassSection, Term

from .calculations import recalculate_class_term


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def recalculate_class_term_task(class_section_id, term_id):
    class_section = ClassSection.objects.get(pk=class_section_id)
    term = Term.objects.get(pk=term_id)
    results = recalculate_class_term(class_section, term)
    return {"calculated": len(results)}
