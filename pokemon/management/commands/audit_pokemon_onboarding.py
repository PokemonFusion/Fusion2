"""Inspect exact saved setup without granting or repairing any character assets."""
import json

from django.core.management.base import BaseCommand, CommandError
from evennia.objects.models import ObjectDB

from pokemon.models.core import OwnedPokemon
from pokemon.models.onboarding import OnboardingCompletion
from pokemon.models.storage import PokemonPlacement, UserStorage
from pokemon.models.trainer import Trainer
from pokemon.services.battle_rewards import BattleRewards
from pokemon.services.onboarding import POLICY


class Command(BaseCommand):
    """Give staff a read-only receipt/draft/custody view for one reviewed character."""

    help = 'Read-only character onboarding inspection; never grants a starter, form, XP or validation.'

    def add_arguments(self, parser):
        """Require the exact character identity rather than an account-wide selector."""
        parser.add_argument('--character', required=True, type=int)

    def handle(self, *args, **options):
        """Avoid typeclass creator properties and expose recovery limits explicitly."""
        character = ObjectDB.objects.filter(pk=options['character']).first()
        if character is None:
            raise CommandError('No character with that ID.')
        trainer = Trainer.objects.filter(user_id=character.pk).first()
        storage = UserStorage.objects.filter(user_id=character.pk).first()
        row = OnboardingCompletion.objects.filter(origin_character_id=character.pk).first()
        report = {'character': character.pk, 'policy': POLICY, 'location': getattr(character.location, 'pk', None),
            'trainer': trainer.pk if trainer else None, 'storage': storage.pk if storage else None,
            'owned_count': OwnedPokemon.objects.filter(trainer=trainer).count() if trainer else 0,
            'placements': list(PokemonPlacement.objects.filter(storage=storage).values('pokemon_id', 'location_type', 'slot')) if storage else [],
            'saved_setup': {key: BattleRewards.stored_attribute(character, key) for key in
                ('validated', 'chargen_completed', 'onboarding_policy', 'chargen_draft', 'gender', 'favored_type', 'fusion_id', 'fusion_forms')},
            'completion': {'id': str(row.pk), 'original_pokemon': str(row.pokemon_uuid), 'receipt': row.receipt} if row else None,
            'recovery': 'Unfinished new setup: reopen chargen. A completed or legacy established character receives no extra grant. Review missing/conflicting state deliberately; this inspection performs no repair.'}
        self.stdout.write(json.dumps(report, default=str, indent=2))
