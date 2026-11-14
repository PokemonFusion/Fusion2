"""Plan or apply the Adventure Hall release from a known public room."""

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from pokemon.adventures.content import AdventureInstallation, CURRENT_CONTENT


class Command(BaseCommand):
    """Expose a read-only plan by default and an explicit apply operation."""

    help = "Validate and plan the Adventure Hall release. Pass --apply to install or upgrade."

    def add_arguments(self, parser):
        """Require the exact public entrance room dbref."""

        parser.add_argument("host", help="Public room dbref such as #123")
        parser.add_argument("--apply", action="store_true", help="Apply this release atomically.")

    def handle(self, *args, **options):
        """Report the complete plan or a concrete installation conflict."""

        try:
            host = int(options["host"].removeprefix("#"))
            installer = AdventureInstallation(host)
            actions = installer.install() if options["apply"] else installer.plan()[0]
        except (ValueError, DatabaseError) as error:
            raise CommandError(f"Adventure content rejected: {error}") from error
        self.stdout.write(f"Adventure content v{CURRENT_CONTENT.version}")
        for action in actions:
            self.stdout.write(action)
