"""Inspect trainer Fusion references and explicitly recover only reviewed bad IDs."""

import json

from django.core.management.base import BaseCommand, CommandError
from evennia.objects.models import ObjectDB

from pokemon.services.fusion_transitions import FusionTransitions
from pokemon.services.placement import PlacementError


class Command(BaseCommand):
    """Read by default; a fingerprint-bound recovery never changes Pokémon owners."""

    help = "Inspect one character's Fusion state; optionally clear reviewed missing/foreign references."

    def add_arguments(self, parser):
        """Make the target and any deliberate recovery explicit in operator commands."""
        parser.add_argument("character", type=int)
        parser.add_argument("--clear-invalid-references", action="store_true")
        parser.add_argument("--fingerprint")
        parser.add_argument("--operator-note")

    def handle(self, *args, **options):
        """Emit an inspectable record or apply only the bounded reviewed operation."""
        try:
            character = ObjectDB.objects.get(pk=options["character"])
            service = FusionTransitions(character)
            if options["clear_invalid_references"]:
                if not options["fingerprint"] or not options["operator_note"]:
                    raise CommandError("Recovery needs the inspected --fingerprint and --operator-note.")
                result = service.clear_invalid_references(options["fingerprint"], operator_note=options["operator_note"])
            else:
                result = service.inspect()
            self.stdout.write(json.dumps(result, indent=2))
        except (ObjectDB.DoesNotExist, PlacementError) as error:
            raise CommandError(str(error)) from error
