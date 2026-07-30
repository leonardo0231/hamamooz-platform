import hashlib
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from hamamooz.apps.academics.calculations import recalculate_class_term
from hamamooz.apps.academics.models import Assessment
from hamamooz.apps.accounts.models import User
from hamamooz.apps.organizations.models import ClassSection, Organization, Term


class Command(BaseCommand):
    help = "Recalculate materialized statistics for one deterministic SQL fixture namespace."

    def add_arguments(self, parser):
        parser.add_argument("--scale", choices=("1k", "10k", "1m"), default="1k")
        parser.add_argument("--organization-id", type=uuid.UUID)
        parser.add_argument(
            "--promote-draft-assessments",
            action="store_true",
            help="Promote only this fixture namespace's draft assessments to locked.",
        )

    def handle(self, *args, **options):
        organization_id = options["organization_id"] or uuid.UUID(
            hashlib.md5(f"load_{options['scale']}:org".encode()).hexdigest()
        )
        try:
            organization = Organization.objects.get(pk=organization_id, is_deleted=False)
        except Organization.DoesNotExist as exc:
            raise CommandError(f"Fixture organization not found: {organization_id}") from exc

        promoted = 0
        if options["promote_draft_assessments"]:
            actor = (
                User.objects.filter(
                    role_assignments__organization=organization,
                    role_assignments__role="teacher",
                    role_assignments__is_active=True,
                    role_assignments__is_deleted=False,
                )
                .order_by("id")
                .first()
            )
            if actor is None:
                raise CommandError("No active fixture teacher is available to review assessments.")
            now = timezone.now()
            promoted = Assessment.objects.filter(
                course_offering__class_section__school__organization=organization,
                status=Assessment.Status.DRAFT,
                is_deleted=False,
            ).update(
                status=Assessment.Status.LOCKED,
                submitted_at=now,
                reviewed_at=now,
                locked_at=now,
                reviewed_by=actor,
                workflow_version=3,
            )

        terms = Term.objects.filter(academic_year__organization=organization).order_by("starts_on")
        classes = ClassSection.objects.filter(school__organization=organization, is_active=True)
        calculated = 0
        for term in terms:
            for class_section in classes:
                calculated += len(recalculate_class_term(class_section, term))
        self.stdout.write(
            self.style.SUCCESS(
                f"Promoted {promoted} assessments and recalculated {calculated} enrollment "
                f"statistics for fixture organization {organization_id}."
            )
        )
