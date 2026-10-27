"""Inspect sealed breeding and egg records without altering outcomes or custody."""

import json
from uuid import UUID

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from pokemon.models.breeding import BreedingCycle, BreedingEgg
from pokemon.services.breeding_audit import audit_breeding_v1
from pokemon.services.ownership_audit import audit_ownership_v2


class Command(BaseCommand):
    """Expose exact retry identities and audit failures without inventing repairs."""

    help = "Read-only breeding/egg inspection; never rerolls, charges, creates or hatches Pokemon."

    def add_arguments(self, parser):
        """Select the database and optionally one exact cycle identity."""
        parser.add_argument("--database", default="default")
        parser.add_argument("--cycle")

    def handle(self, *args, **options):
        """Preserve historical traits, parent cooldowns and released-egg receipts."""
        cycles = BreedingCycle.objects.using(options["database"]).order_by("started_at")
        if options["cycle"]:
            try:
                identifier = UUID(options["cycle"])
            except ValueError as error:
                raise CommandError("Use the full cycle UUID.") from error
            cycles = cycles.filter(pk=identifier)
            if not cycles.exists():
                raise CommandError("No such cycle. No data was changed.")
        for cycle in cycles.values():
            self.stdout.write(json.dumps(cycle, default=str, sort_keys=True))
            egg = BreedingEgg.objects.using(options["database"]).filter(cycle_id=cycle["id"]).values().first()
            if egg:
                self.stdout.write(json.dumps(egg, default=str, sort_keys=True))
        problems = list(audit_ownership_v2(apps, options["database"])) + list(audit_breeding_v1(apps, options["database"]))
        for problem in problems:
            self.stdout.write(str(problem))
        if problems:
            raise CommandError("Breeding/custody needs deliberate review. No traits, fees, claims or assets were changed.")
        self.stdout.write("Records are consistent. The origin character can retry collect/cancel; the egg's current owner can retry hatch. "
                          "Never delete cooldowns, reroll plans or recreate a released egg. No data was changed.")
