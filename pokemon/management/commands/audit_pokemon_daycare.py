"""Inspect canonical Daycare custody and receipts without changing player assets."""

import json
from uuid import UUID

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from pokemon.models.daycare import DaycareEntry
from pokemon.services.ownership_audit import audit_ownership_v2


class Command(BaseCommand):
    """Give staff exact entry/claim identities and the ordinary recovery route."""

    help = "Read-only Daycare custody inspection; no automatic payment, moves or repairs."

    def add_arguments(self, parser):
        """Select an alias and optionally one exact entry or active entries only."""
        parser.add_argument("--database", default="default")
        parser.add_argument("--entry")
        parser.add_argument("--active", action="store_true")

    def handle(self, *args, **options):
        """Never infer custody from a missing record or invent a replacement claim."""
        entries = DaycareEntry.objects.using(options["database"]).order_by("deposited_at")
        if options["entry"]:
            try:
                identifier = UUID(options["entry"])
            except ValueError as error:
                raise CommandError("Use a full Daycare entry UUID.") from error
            entries = entries.filter(pk=identifier)
            if not entries.exists():
                raise CommandError("No such Daycare entry. No data was changed.")
        if options["active"]:
            entries = entries.filter(state="active")
        for entry in entries.values("id", "storage__user_id", "owned_id", "state", "place", "fee", "active_cycle_id", "receipt"):
            self.stdout.write(json.dumps(entry, default=str, sort_keys=True))
        problems = list(audit_ownership_v2(apps, options["database"]))
        for problem in problems:
            self.stdout.write(str(problem))
        if problems:
            raise CommandError("Custody requires deliberate review. No assets, claims, fees or receipts were changed.")
        self.stdout.write("Custody is consistent. Retry +daycare retrieve ENTRY_ID as the owning character; "
                          "completed retrieval returns its historical receipt. No data was changed.")
