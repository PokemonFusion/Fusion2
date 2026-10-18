"""Atomic ordinary-player launch of configured production gym encounters."""

from __future__ import annotations

from pokemon.battle.battleinstance import BattleSession
from pokemon.helpers.party_helpers import pokemon_is_usable
from pokemon.services.battle_rewards import BattleRewards
from pokemon.services.gym_leaders import GymLeaderError, _resolve_gym_leader_profile, generate_gym_leader_encounter
from utils.fusion import get_battle_party_with_fusion


class GymChallenge:
    """Serialize eligibility and launch on the character's existing battle lock."""

    def __init__(self, player, identifier):
        """Keep the transport separate from the row used for serialization."""
        self.player = player
        self.identifier = identifier

    def start(self):
        """Commit the complete session or roll back its startup database writes."""
        from django.db import transaction
        from evennia.objects.models import ObjectDB

        session = None
        allocated = False
        character = BattleRewards.character(self.player)
        try:
            with transaction.atomic():
                ObjectDB.objects.select_for_update().get(pk=character.pk)
                character.attributes.reset_cache()
                if (getattr(self.player.db, "battle_id", None) is not None
                        or getattr(self.player.db, "battle_lock", None) not in (None, False, "")
                        or BattleSession.ensure_for_player(self.player)):
                    raise GymLeaderError("Finish your current battle before starting a gym challenge.")
                profile = _resolve_gym_leader_profile(self.identifier)
                profile = type(profile).objects.select_for_update().get(pk=profile.pk)
                if profile.content_stage != "production":
                    raise GymLeaderError("Test gyms are not available through the production challenge path.")
                encounter = generate_gym_leader_encounter(profile, player=self.player)
                required = 2 if encounter.battle_format == "double" else 1
                if sum(pokemon_is_usable(mon) for mon in get_battle_party_with_fusion(self.player)) < required:
                    raise GymLeaderError(f"You need at least {required} conscious Pokemon for this gym.")
                allocated = True
                session = BattleSession(self.player)
                session.start_trainer_encounter(encounter)
            return session, encounter
        except Exception:
            # Encounter rows, locks and room checkpoints share this transaction.
            # Only non-persistent runtime references need releasing after rollback.
            character.attributes.reset_cache()
            if allocated:
                self._release_runtime(session or getattr(self.player.ndb, "battle_instance", None))
            raise

    def _release_runtime(self, session):
        """Drop only the failed attempt's runtime cache; never finalize its battle."""
        from pokemon.battle.handler import battle_handler

        if session is None:
            return
        battle_handler.unregister(session)
        room = getattr(session, "room", None)
        if room is not None:
            if getattr(room, "attributes", None) is not None:
                room.attributes.reset_cache()
            instances = getattr(room.ndb, "battle_instances", None) or {}
            instances.pop(session.battle_id, None)
        if getattr(self.player.ndb, "battle_instance", None) is session:
            self.player.ndb.battle_instance = None
