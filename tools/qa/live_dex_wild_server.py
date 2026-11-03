"""Prepare one disposable wild encounter in the existing guarded QA room."""

import importlib.util
import random
from pathlib import Path
from types import SimpleNamespace

_spec = importlib.util.spec_from_file_location(
    "pf2_wild_guarded_dex", Path(__file__).with_name("live_dex_server.py")
)
_dex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dex)


def start_wild(path, payload):
    """Create a new tracked encounter; choices remain ordinary player commands."""
    from pokemon.battle.battleinstance import BattleSession
    from pokemon.battle.engine import BattleType
    from pokemon.battle.pokemon_factory import create_battle_pokemon

    _, _, room, players, _ = _dex._pilot.guarded_context(path)
    if _dex._pilot.active_session(players) or room.db.battles or room.db.pvp_requests:
        raise RuntimeError("Finish the previous QA battle before wild setup.")
    if any(players[label].db.battle_lock or players[label].db.battle_id for label in ("a", "b")):
        raise RuntimeError("QA battle locks must be clear before wild setup.")
    wild = create_battle_pokemon(payload["species"], int(payload["level"]),
                                 is_wild=True, move_names=["Splash"])
    if not str(getattr(wild, "model_id", "")).startswith("encounter:"):
        raise RuntimeError("Disposable wild encounter was not durably created.")
    # Only this newly constructed foe is prepared. No existing Pokemon or
    # shared dex entry is changed, and no callback is replaced.
    wild.ability = payload["ability"]
    try:
        session = BattleSession(players["a"], rng=random.Random(int(payload["seed"])))
    except Exception:
        from pokemon.services.encounters import delete_encounter_by_ref

        delete_encounter_by_ref(wild.model_id)
        raise
    session.temp_pokemon_ids.append(wild.model_id)
    shell = SimpleNamespace(name="QA wild " + wild.name, key="QA wild " + wild.name,
                            team=[wild], active_pokemon=wild, is_wild=True, is_npc=False,
                            ai_profile="wild_basic", ndb=SimpleNamespace(), db=SimpleNamespace())
    session.captainB = shell
    session.trainers = [players["a"], shell]
    session._register_trainer(shell)
    session._init_battle_state(room, session._prepare_player_party(players["a"]),
                              wild, shell.name, BattleType.WILD, opponent_team=[wild])
    session._setup_battle_room(intro_message="A disposable QA wild encounter begins.")
    result = _dex.snapshot(path)
    result["new_encounter_ref"] = wild.model_id
    return result


def dispatch(path, action, payload=None):
    """Extend the guarded staff API with fixture preparation, never choices."""
    if action == "start_wild":
        return start_wild(path, payload or {})
    if action == "encounter_exists":
        from pokemon.services.encounters import get_encounter_from_ref

        _dex._pilot.guarded_context(path)
        return {"exists": get_encounter_from_ref((payload or {})["ref"]) is not None}
    return _dex.dispatch(path, action, payload)
