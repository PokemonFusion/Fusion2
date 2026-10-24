"""Character-scoped, resumable setup and one-time starter/Fusion completion."""

from collections.abc import Mapping
from uuid import uuid4

from django.db import transaction

from pokemon.services.battle_rewards import BattleRewards
from pokemon.services.fusion_transitions import reset_fusion_cache
from pokemon.services.ownership import acting_character, assert_character_free, locked_owners
from pokemon.services.placement import PlacementError, PlacementService

DRAFT_FIELDS = {'type', 'player_gender', 'favored_type', 'species_key', 'species', 'ability', 'nature', 'starter_gender'}
POLICY = 'self_service_beta_v1'


class OnboardingError(PlacementError):
    """Refuse inconsistent setup without granting any partial resources."""


class Onboarding:
    """Persist choices separately from the atomic, durable completion receipt."""

    def __init__(self, actor):
        """Accept only the current character, never an account-wide character ID."""
        self.character = acting_character(actor)
        self.actor_id = self.character.pk

    def completion(self):
        """Return this character's historical receipt even after later asset release."""
        from pokemon.models.onboarding import OnboardingCompletion
        return OnboardingCompletion.objects.filter(origin_character_id=self.actor_id).first()

    def draft(self):
        """Read saved choices directly, avoiding a disconnected client's stale cache."""
        value = BattleRewards.stored_attribute(self.character, 'chargen_draft') or {}
        if not isinstance(value, Mapping):
            raise OnboardingError('Your saved setup needs review; no new Pokemon was created.')
        return {key: str(value[key]) for key in DRAFT_FIELDS if key in value and isinstance(value[key], str)}

    @staticmethod
    def _legacy(character, trainer):
        """Do not guess another free grant for an already-established legacy character."""
        from pokemon.models.core import OwnedPokemon
        return bool(BattleRewards.stored_attribute(character, 'validated')
            or BattleRewards.stored_attribute(character, 'chargen_completed')
            or BattleRewards.stored_attribute(character, 'fusion_id')
            or BattleRewards.stored_attribute(character, 'fusion_species')
            or (BattleRewards.stored_attribute(character, 'gender') and BattleRewards.stored_attribute(character, 'favored_type'))
            or OwnedPokemon.objects.filter(trainer=trainer).exists())

    def save_draft(self, choices):
        """Save accepted menu choices without issuing a starter, form or other grant."""
        from evennia.objects.models import ObjectDB
        from pokemon.models.trainer import Trainer
        if not isinstance(choices, Mapping):
            raise OnboardingError('Setup choices must come from the character menu.')
        data = {key: choices[key] for key in DRAFT_FIELDS if key in choices}
        if any(not isinstance(value, str) or len(value) > 255 for value in data.values()):
            raise OnboardingError('A setup choice is invalid; reopen chargen and select it again.')
        with transaction.atomic():
            ObjectDB.objects.select_for_update(no_key=True).filter(pk=self.actor_id).values('pk').get()
            trainer = Trainer.objects.filter(user_id=self.actor_id).first()
            if trainer is None:
                raise OnboardingError('Your character setup record is unavailable; no grant was made.')
            if self.completion() or self._legacy(self.character, trainer):
                raise OnboardingError('Character setup is already complete; no additional starter or form can be granted.')
            self.character.attributes.add('chargen_draft', data)
        return data

    def resume(self):
        """Choose the next menu node from persisted accepted choices."""
        data = self.draft()
        self.character.ndb.chargen = dict(data)
        kind = data.get('type')
        if kind not in {'human', 'fusion'}:
            return 'start', {}
        if data.get('player_gender') not in {'Male', 'Female'}:
            return kind + '_gender', {}
        if kind == 'human' and not data.get('favored_type'):
            return 'human_type', {'gender': data['player_gender']}
        if not data.get('species_key'):
            return ('starter_species', {'type': data.get('favored_type')}) if kind == 'human' else ('fusion_species', {})
        if not data.get('ability'):
            return ('starter_ability' if kind == 'human' else 'fusion_ability'), {}
        if not data.get('nature'):
            return ('starter_nature' if kind == 'human' else 'fusion_nature'), {}
        if kind == 'human' and not data.get('starter_gender'):
            return 'starter_gender', {'resume_nature': data['nature']}
        return ('starter_confirm' if kind == 'human' else 'fusion_confirm'), {}

    @staticmethod
    def validate(data, kind):
        """Recheck native species/ability/nature and all required choices at commit."""
        from pokemon.data.generation import NATURES
        from pokemon.data.starters import is_valid_starter_key, resolve_starter_key
        from pokemon.dex import POKEDEX
        from pokemon.names import normalize_name, resolve_dex_entry
        if kind not in {'human', 'fusion'} or data.get('type') != kind:
            raise OnboardingError('Your setup path changed. Reopen chargen to review the saved choices.')
        if data.get('player_gender') not in {'Male', 'Female'} or data.get('nature') not in NATURES:
            raise OnboardingError('Choose a valid gender and nature in chargen before finishing.')
        species = resolve_dex_entry(POKEDEX, data.get('species_key'))
        if species is None or any(species.raw.get(key) for key in ('battleOnly', 'requiredItem', 'requiredItems', 'requiredAbility')):
            raise OnboardingError('Choose a supported native species in chargen; battle activation forms cannot be starting bodies.')
        abilities = {normalize_name(getattr(value, 'name', value)): getattr(value, 'name', value) for value in species.abilities.values()}
        ability = abilities.get(normalize_name(data.get('ability')))
        if not ability:
            raise OnboardingError('Choose one of that species\' native abilities before finishing.')
        if kind == 'human':
            key = resolve_starter_key(data.get('species_key'))
            if not key or not is_valid_starter_key(key):
                raise OnboardingError('Choose a valid starter from +starters.')
            from menus.chargen import TYPES
            if data.get('favored_type') not in TYPES:
                raise OnboardingError('Choose your favored type in chargen.')
            gender = data.get('starter_gender')
            fixed = getattr(species, 'gender', None)
            if (fixed in {'M', 'F', 'N'} and gender != fixed) or (fixed not in {'M', 'F', 'N'} and gender not in {'M', 'F'}):
                raise OnboardingError('Choose a valid gender for that starter.')
        else:
            # Fusion represents this trainer's personal body; retain the chosen
            # presentation gender, including species with no native gender.
            gender = data['player_gender'][0]
        return species, ability, gender

    def complete(self, kind, *, expected_choices=None):
        """Commit exactly one starter or initial permanent form and its receipt."""
        from pokemon.data.generation import generate_pokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.onboarding import OnboardingCompletion

        created_id = None
        try:
            with locked_owners((self.actor_id,)) as (characters, storages, trainers):
                character, storage, trainer = characters[self.actor_id], storages[self.actor_id], trainers[self.actor_id]
                old = self.completion()
                if old:
                    return old.receipt
                assert_character_free(character)
                if self._legacy(character, trainer):
                    raise OnboardingError('This character already has saved setup or Pokemon. No extra starter or form was created. Use +sheet and help getting started; staff can inspect inconsistent legacy setup.')
                if character.location is None:
                    raise OnboardingError('Your starting location is unavailable. No resources were created; please try again later.')
                data = self.draft()
                reviewed = {key: expected_choices[key] for key in DRAFT_FIELDS if key in expected_choices} if isinstance(expected_choices, Mapping) else None
                if reviewed != data:
                    raise OnboardingError("Your saved choices changed or have not been reviewed. Reopen chargen and confirm the current choices; no Pokemon was granted.")
                species, ability, gender = self.validate(data, kind)
                instance = generate_pokemon(species.name, level=5)
                created_id = uuid4()
                pokemon = create_owned_pokemon(species.name, trainer, 5, unique_id=created_id,
                    ability=ability, gender=gender, nature=data['nature'],
                    ivs=[getattr(instance.ivs, key) for key in ('hp', 'attack', 'defense', 'special_attack', 'special_defense', 'speed')],
                    evs=[0]*6, active_move_names=list(instance.moves), obtained_method='starter' if kind == 'human' else 'initial_fusion',
                    original_trainer=trainer, original_trainer_name=character.key[:100])
                if not pokemon.activemoveslot_set.exists():
                    raise OnboardingError('Starting moves could not be saved. Your previous setup was retained; try again.')
                character.attributes.add('gender', data['player_gender'])
                character.attributes.add('morphology', 'Human' if kind == 'human' else 'Fusion')
                if kind == 'human':
                    character.attributes.add('favored_type', data['favored_type'])
                else:
                    PlacementService(storage).reserve_for_fusion(pokemon)
                    for key, value in {'fusion_id': str(created_id), 'fusion_kind': 'permanent', 'fusion_forms': [str(created_id)],
                            'fusion_species': pokemon.species, 'fusion_ability': pokemon.ability, 'fusion_nature': pokemon.nature,
                            'level': pokemon.level, 'total_exp': pokemon.total_exp, 'fighter_xp': pokemon.total_exp,
                            'fusion_participates': True}.items():
                        character.attributes.add(key, value)
                receipt = {'character': self.actor_id, 'kind': kind, 'pokemon': str(created_id),
                    'species': pokemon.species, 'ability': pokemon.ability, 'nature': pokemon.nature,
                    'gender': pokemon.gender, 'level': pokemon.level, 'total_exp': pokemon.total_exp,
                    'start_location': character.location.pk, 'policy': POLICY}
                OnboardingCompletion.objects.create(character=character, origin_character_id=self.actor_id,
                    pokemon=pokemon, pokemon_uuid=created_id, kind=kind, choices=data, receipt=receipt)
                character.attributes.add('chargen_completed', True)
                character.attributes.add('onboarding_policy', POLICY)
                character.attributes.remove('chargen_draft')
                transaction.on_commit(lambda: setattr(character.ndb, 'chargen', {}))
                return receipt
        finally:
            reset_fusion_cache(self.character, pokemon_ids=(created_id,) if created_id else ())
            if created_id:
                cached = OwnedPokemon.get_cached_instance(created_id)
                if cached is not None and not OwnedPokemon.objects.filter(pk=created_id).exists():
                    OwnedPokemon.flush_cached_instance(cached)
