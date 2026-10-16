"""Player launch policy for explicitly enabled, placed static trainers."""

from __future__ import annotations

import math
import time
from collections.abc import Mapping
from dataclasses import replace
from types import SimpleNamespace

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
        retry_trainer_challenge_cleanup(self.player)
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
        if battle_format == "double":
            raise TrainerEncounterError(
                "Double trainer challenges are not available yet: player commands cannot select both active Pokemon. "
                "Ask staff to set battle_format to 'single' until doubles action and target selection is supported (#708)."
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
        required = 1
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
            # __init__ may register the player before it fails to return.
            session = session or getattr(self.player.ndb, "battle_instance", None)
            refs = [mon.model_id for mon in encounter.team if getattr(mon, "model_id", None)]
            pending = {"battle_id": getattr(session, "battle_id", None),
                       "room_id": getattr(self.player.location, "id", None),
                       "npc_id": self.npc.id, "encounter_refs": refs}
            if session is not None:
                session.placed_trainer = self.npc
                session._challenge_cleanup = pending
                session.temp_pokemon_ids = list(dict.fromkeys([
                    *getattr(session, "temp_pokemon_ids", []), *refs,
                ]))
            try:
                # The receipt also covers disconnect/reload before cleanup can
                # finish. Keep it and the generated rows if cleanup is unavailable.
                self.player.db.pending_trainer_challenge_cleanup = pending
                retry_trainer_challenge_cleanup(self.player)
            except Exception as error:
                raise TrainerEncounterError(
                    "Trainer challenge startup failed and cleanup is still pending. "
                    "Use +challenge/retry before starting another battle."
                ) from error
            raise
        self.npc.db.trainer_challenge_next_at = self.now + cooldown
        return session, encounter


def retry_trainer_challenge_cleanup(player):
    """Finish one failed startup, retaining its receipt until every step succeeds."""
    session = getattr(player.ndb, "battle_instance", None)
    pending = getattr(player.db, "pending_trainer_challenge_cleanup", None)
    pending = pending or getattr(session, "_challenge_cleanup", None)
    if not pending:
        return False
    battle_id = pending.get("battle_id")
    if battle_id is not None:
        # Check before restoration: _register_trainer during restore writes locks.
        for attr in ("battle_lock", "battle_id"):
            value = getattr(player.db, attr, None)
            if value not in (None, False, "") and str(value) != str(battle_id):
                raise TrainerEncounterError("Finish your current battle before retrying the old challenge cleanup.")
    if session is None and battle_id is not None:
        from pokemon.battle.handler import battle_handler

        session = battle_handler.get(battle_id) or BattleSession.ensure_for_player(player)
    if session is not None:
        if session.battle_id != battle_id:
            raise TrainerEncounterError("Finish your current battle before retrying the old challenge cleanup.")
        session.end()
    elif battle_id is not None:
        _cleanup_orphaned_start(player, pending)

    from pokemon.services.encounters import delete_encounter_by_ref

    npc = getattr(session, "placed_trainer", None)
    if npc is None:
        from evennia.objects.models import ObjectDB

        npc = ObjectDB.objects.filter(pk=pending["npc_id"]).first()
    release_placed_trainer(SimpleNamespace(placed_trainer=npc, battle_id=battle_id))
    for ref in pending["encounter_refs"]:
        delete_encounter_by_ref(ref)
    player.db.pending_trainer_challenge_cleanup = None
    if session is not None:
        session._challenge_cleanup = None
    return True


def _cleanup_orphaned_start(player, pending):
    """Release recorded constructor debris after reload without touching other battles."""
    from evennia.objects.models import ObjectDB

    from pokemon.battle.storage import BattleDataWrapper
    from utils.locks import clear_battle_lock

    battle_id = pending["battle_id"]
    room = ObjectDB.objects.filter(pk=pending["room_id"]).first()
    if room is not None:
        storage = BattleDataWrapper(room, battle_id)
        for part in ("logic", "trainers", "temp_pokemon_ids", "encounter", "battle_result",
                     "data", "state", "meta", "field", "active", "last_action", "debug"):
            storage.delete(part)
        room.db.battles = [bid for bid in (room.db.battles or []) if str(bid) != str(battle_id)]
        instances = getattr(room.ndb, "battle_instances", None)
        if instances:
            instances.pop(battle_id, None)
    clear_battle_lock(player)
    player.db.battle_id = None
    player.db.battle_control = False


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
