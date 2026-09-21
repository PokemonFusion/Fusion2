"""Report invalid lifecycle records without modifying player data."""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from pokemon.services.placement_audit import audit_placements_v1


class Command(BaseCommand):
    """Print every detected problem and exit nonzero when staff action is needed."""

    help = "Read-only audit of Pokemon ownership, canonical placement, and legacy mirrors."

    def add_arguments(self, parser):
        """Allow auditing a configured database alias."""
        parser.add_argument("--database", default="default")

    def handle(self, *args, **options):
        """Emit actionable identifiers; never guess owners or perform repairs."""
        count = 0
        for problem in audit_placements_v1(apps, options["database"]):
            self.stdout.write(str(problem))
            count += 1
        if count:
            raise CommandError(f"{count} placement problems require staff review. No data was changed.")
        self.stdout.write(self.style.SUCCESS("All owned Pokemon have valid canonical placements and mirrors."))
