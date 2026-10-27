"""Inspect canonical custody, exclusive claims and outstanding transfer receipts."""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from pokemon.models.ownership import OwnershipTransfer
from pokemon.services.ownership_audit import audit_ownership_v2


class Command(BaseCommand):
    """Read-only staff inspection; no automatic acceptance, moves or repairs."""

    help = "Read-only ownership/reservation audit and outstanding transfer identities."

    def add_arguments(self, parser):
        """Select a configured alias and optionally list pending operations."""
        parser.add_argument("--database", default="default")
        parser.add_argument("--pending", action="store_true")

    def handle(self, *args, **options):
        """Print exact references for deliberate investigation and safe cancellation."""
        problems = list(audit_ownership_v2(apps, options["database"]))
        for problem in problems:
            self.stdout.write(str(problem))
        if options["pending"]:
            for operation in OwnershipTransfer.objects.using(options["database"]).filter(state="pending").order_by("created_at"):
                status = "expired; cancel to release" if operation.expires_at <= timezone.now() else "awaiting consent/commit"
                self.stdout.write(f"{operation.pk}: characters={operation.proposer_id},{operation.recipient_id}; "
                                  f"approvals={operation.approvals}; {status}")
        if problems:
            raise CommandError(f"{len(problems)} ownership problems require review. No data was changed.")
        self.stdout.write(self.style.SUCCESS("Custody and reservations are consistent. No data was changed."))
