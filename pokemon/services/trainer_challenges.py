"""Player launch policy for explicitly enabled, placed static trainers."""

from __future__ import annotations

import math
import time
from collections.abc import Mapping
from dataclasses import replace

from pokemon.battle.battleinstance import BattleSession
from pokemon.helpers.party_helpers import pokemon_is_usable
from pokemon.services.trainer_encounters import (
    TrainerEncounterError,
    _npc_trainer_model,
    check_static_trainer,
    generate_static_trainer_encounter,
)
from utils.fusion import get_battle_party_with_fusion


class TrainerChallenge:
    """Validate placement and policy before allocating encounter or session data."""

    def __init__(self, player, npc, *, now=None):
        self.player = player
        self.npc = npc
        self.now = time.time() if now is None else now

    def _check_session(self, actor, label):
        """Fail closed on live, persistent, or unresolved battle references."""
        db = actor.db
        if (
            getattr(db, "battle_id", None) is not None
            or getattr(db, "battle_lock", None) not in (None, False, "")
            or BattleSession.ensure_for_player(actor)
        ):
            raise TrainerEncounterError(f"{label} is already in a battle. Finish it before challenging again.")

    def start(self):
        """Start through the shared encounter adapter, preserving the entire team."""
        if self.player.location is None or self.npc.location != self.player.location:
            raise TrainerEncounterError("You must be in the same room as that trainer.")
        config = getattr(self.npc.db, "trainer_challenge", None)
        if not isinstance(config, Mapping) or config.get("enabled") is not True:
            raise TrainerEncounterError("That NPC is not accepting trainer challenges.")
        unknown = set(config) - {"enabled", "battle_format", "cooldown_seconds"}
        if unknown:
            raise TrainerEncounterError(
                "That trainer has unsupported challenge rules. Ask staff to check its configuration."
            )
        battle_format = config.get("battle_format", "single")
        if not isinstance(battle_format, str) or battle_format not in {"single", "double"}:
            raise TrainerEncounterError(
                "That trainer has an invalid battle format. Ask staff to check its configuration."
            )
        cooldown = config.get("cooldown_seconds", 0)
        next_at = getattr(self.npc.db, "trainer_challenge_next_at", None) or 0
        if (
            isinstance(cooldown, bool)
            or not isinstance(cooldown, (int, float))
            or cooldown < 0
            or not math.isfinite(cooldown)
            or not isinstance(next_at, (int, float))
            or not math.isfinite(next_at)
        ):
            raise TrainerEncounterError("That trainer has an invalid cooldown. Ask staff to check its configuration.")
        self._check_session(self.player, "Your character")
        self._check_session(self.npc, "That trainer")
        if self.now < next_at:
            raise TrainerEncounterError(f"That trainer is resting. Try again in {int(next_at - self.now) + 1} seconds.")
        required = 2 if battle_format == "double" else 1
        party = get_battle_party_with_fusion(self.player)
        if sum(pokemon_is_usable(mon) for mon in party) < required:
            raise TrainerEncounterError(
                f"You need at least {required} conscious Pokemon in your party for this challenge."
            )
        trainer_id = getattr(self.npc.db, "npc_trainer_id", None)
        if isinstance(trainer_id, bool) or not isinstance(trainer_id, int) or trainer_id < 1:
            raise TrainerEncounterError("That NPC has no valid trainer link. Ask staff to set npc_trainer_id.")
        trainer = _npc_trainer_model().objects.filter(pk=trainer_id).first()
        if trainer is None:
            raise TrainerEncounterError("That NPC's trainer record is missing. Ask staff to repair its trainer link.")
        check = check_static_trainer(trainer)
        if not check.can_start_battle or check.warnings or not required <= check.template_count <= 6:
            raise TrainerEncounterError(
                "That trainer's team is not ready. Ask staff to run +npcbattle/check " + trainer.name + "."
            )
        # Gym progression must use its own eligibility/result service.
        if getattr(trainer, "gym_leader_profile", None) is not None:
            raise TrainerEncounterError("This is a gym leader. Use +gym challenge for the gym eligibility checks.")
        encounter = generate_static_trainer_encounter(trainer)
        encounter = replace(
            encounter, battle_format=battle_format, metadata={**encounter.metadata, "placed_npc_id": self.npc.id}
        )
        session = None
        try:
            session = BattleSession(self.player)
            session.placed_trainer = self.npc
            self.npc.db.battle_id = session.battle_id
            self.npc.ndb.battle_instance = session
            session.start_trainer_encounter(encounter)
        except Exception:
            try:
                if session is not None:
                    session.end()
            finally:
                if session is not None:
                    release_placed_trainer(session)
                from pokemon.services.encounters import delete_encounter_by_ref

                for mon in encounter.team:
                    ref = getattr(mon, "model_id", None)
                    if ref:
                        delete_encounter_by_ref(ref)
            raise
        self.npc.db.trainer_challenge_next_at = self.now + cooldown
        return session, encounter


def release_placed_trainer(session):
    """Release this session's placed NPC, including after session restoration."""
    npc = getattr(session, "placed_trainer", None)
    if npc is None:
        npc_id = (getattr(session, "encounter_metadata", None) or {}).get("placed_npc_id")
        if npc_id:
            from evennia.utils.search import search_object

            matches = search_object(f"#{npc_id}")
            npc = matches[0] if matches else None
    if npc is not None and getattr(npc.db, "battle_id", None) == session.battle_id:
        npc.db.battle_id = None
        npc.ndb.battle_instance = None
