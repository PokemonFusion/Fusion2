"""Helpers for differential battle validation against Pokemon Showdown."""

from __future__ import annotations

import json
import subprocess
import types
from pathlib import Path
from typing import Any, Dict, List

from pokemon.battle.actions import ActionType

from .helpers import load_modules

ROOT = Path(__file__).resolve().parents[4]
SHOWDOWN_ROOT = ROOT / "pokemon-showdown"
SHOWDOWN_RUNNER = Path(__file__).with_name("showdown_diff_runner.js")


def _normalized_key(value: str) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _raw_entry(entry: Any) -> Dict[str, Any]:
    raw = getattr(entry, "raw", None)
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(entry, dict):
        return dict(entry)
    return {}


def _canonical_boosts(boosts: Dict[str, Any]) -> Dict[str, int]:
    aliases = {
        "attack": "atk",
        "defense": "def",
        "special_attack": "spa",
        "special_defense": "spd",
        "speed": "spe",
    }
    canonical: Dict[str, int] = {}
    for key, value in (boosts or {}).items():
        canonical[aliases.get(str(key), str(key))] = int(value)
    return {key: canonical[key] for key in sorted(canonical)}


def _calc_stat(base: int, iv: int, ev: int, level: int, *, is_hp: bool = False) -> int:
    if is_hp:
        return int(((2 * base + iv + ev // 4) * level) / 100) + level + 10
    return int(((2 * base + iv + ev // 4) * level) / 100) + 5


def _species_hp(species: str, level: int, pokedex: Dict[str, Any]) -> int:
    entry = (
        pokedex.get(species)
        or pokedex.get(str(species).lower())
        or pokedex.get(str(species).capitalize())
    )
    if entry is None:
        return 100
    base_stats = getattr(entry, "base_stats", None)
    if base_stats is None and isinstance(entry, dict):
        base_stats = entry.get("baseStats")
    if base_stats is None:
        return 100
    base_hp = getattr(base_stats, "hp", None)
    if base_hp is None and isinstance(base_stats, dict):
        base_hp = base_stats.get("hp")
    if base_hp is None:
        return 100
    return _calc_stat(int(base_hp), 31, 0, level, is_hp=True)


def _species_stats(species: str, level: int, pokedex: Dict[str, Any]) -> Dict[str, int]:
    entry = (
        pokedex.get(species)
        or pokedex.get(str(species).lower())
        or pokedex.get(str(species).capitalize())
    )
    if entry is None:
        return {
            "hp": 100,
            "attack": 100,
            "defense": 100,
            "special_attack": 100,
            "special_defense": 100,
            "speed": 100,
        }
    base_stats = getattr(entry, "base_stats", None)
    if base_stats is None and isinstance(entry, dict):
        base_stats = entry.get("baseStats")
    if base_stats is None:
        return {
            "hp": _species_hp(species, level, pokedex),
            "attack": 100,
            "defense": 100,
            "special_attack": 100,
            "special_defense": 100,
            "speed": 100,
        }

    def _base_value(key: str, fallback: int = 100) -> int:
        if isinstance(base_stats, dict):
            value = base_stats.get(key)
        else:
            value = getattr(base_stats, key, None)
        if value is None:
            return fallback
        return int(value)

    return {
        "hp": _calc_stat(_base_value("hp"), 31, 0, level, is_hp=True),
        "attack": _calc_stat(_base_value("atk"), 31, 0, level),
        "defense": _calc_stat(_base_value("def"), 31, 0, level),
        "special_attack": _calc_stat(_base_value("spa"), 31, 0, level),
        "special_defense": _calc_stat(_base_value("spd"), 31, 0, level),
        "speed": _calc_stat(_base_value("spe"), 31, 0, level),
    }


def _move_display_name(move_name: str, movedex: Dict[str, Any]) -> str:
    entry = movedex.get(_normalized_key(move_name))
    if entry is None:
        return str(move_name)
    raw = _raw_entry(entry)
    return str(raw.get("name") or getattr(entry, "name", move_name))


def _build_battle_move(move_name: str, movedex: Dict[str, Any], modules: Dict[str, Any]):
    BattleMove = modules["BattleMove"]
    key = _normalized_key(move_name)
    entry = movedex.get(key)
    raw = _raw_entry(entry)
    return BattleMove(
        name=str(raw.get("name") or move_name),
        key=key,
        power=int(raw.get("basePower", 0) or 0),
        accuracy=raw.get("accuracy", True),
        priority=int(raw.get("priority", 0) or 0),
        type=raw.get("type"),
        raw=raw,
        pp=raw.get("pp"),
    )


def _build_move_slot(move_name: str, movedex: Dict[str, Any], modules: Dict[str, Any]):
    Move = modules["Move"]
    key = _normalized_key(move_name)
    entry = movedex.get(key)
    raw = _raw_entry(entry)
    move = Move(name=str(raw.get("name") or move_name), priority=int(raw.get("priority", 0) or 0))
    move.key = key
    move.pp = raw.get("pp")
    move.power = int(raw.get("basePower", 0) or 0)
    move.accuracy = raw.get("accuracy", True)
    move.type = raw.get("type")
    move.category = raw.get("category")
    move.flags = dict(raw.get("flags", {}) or {})
    move.raw = raw
    return move


def _resolve_starting_hp(mon_data: Dict[str, Any], max_hp: int) -> int:
    hp_value = mon_data.get("hp")
    if hp_value is not None:
        try:
            resolved = int(hp_value)
        except Exception:
            resolved = max_hp
        return max(1, min(max_hp, resolved))
    hp_percent = mon_data.get("hp_percent")
    if hp_percent is not None:
        try:
            percent = float(hp_percent)
        except Exception:
            percent = 100.0
        resolved = int(max_hp * max(0.0, min(100.0, percent)) / 100.0)
        return max(1, min(max_hp, resolved))
    return max_hp


def _build_battle_from_scenario(scenario: Dict[str, Any]):
    modules = load_modules()
    Pokemon = modules["Pokemon"]
    Battle = modules["Battle"]
    BattleParticipant = modules["BattleParticipant"]
    BattleType = modules["BattleType"]
    import pokemon.dex as dex_mod  # type: ignore

    movedex = getattr(dex_mod, "MOVEDEX", {})
    pokedex = getattr(dex_mod, "POKEDEX", {})
    participants = []
    team_ids = ("A", "B", "C", "D")

    for idx, side in enumerate(("p1", "p2")):
        team_data = scenario[side]["team"]
        pokemons = []
        for slot, mon_data in enumerate(team_data):
            species = str(mon_data["species"])
            level = int(mon_data.get("level", 100))
            ivs = [31, 31, 31, 31, 31, 31]
            evs = [0, 0, 0, 0, 0, 0]
            max_hp = _species_hp(species, level, pokedex)
            current_hp = _resolve_starting_hp(mon_data, max_hp)
            stats = _species_stats(species, level, pokedex)
            moves = [_build_move_slot(move_name, movedex, modules) for move_name in mon_data.get("moves", [])]
            pokemon = Pokemon(
                species,
                level=level,
                hp=current_hp,
                max_hp=max_hp,
                moves=moves,
                ability=mon_data.get("ability"),
                item=mon_data.get("item"),
                ivs=ivs,
                evs=evs,
                nature="Hardy",
                gender=mon_data.get("gender", "N"),
            )
            pokemon.species = species
            pokemon.base_stats = dict(stats)
            pokemon.side_index = idx
            pokemon.team_slot = slot
            pokemons.append(pokemon)

        participant = BattleParticipant(side.upper(), pokemons, is_ai=False, team=team_ids[idx])
        participants.append(participant)

    battle = Battle(BattleType.TRAINER, participants)
    battle.debug = False
    battle.log_action = lambda *_args, **_kwargs: None
    battle.start_battle()

    for part in battle.participants:
        for poke in part.pokemons:
            poke.battle = battle
            poke.side = part.side
            poke.party = list(part.pokemons)

    return battle, movedex, modules


def _snapshot_pokemon(pokemon) -> Dict[str, Any]:
    item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
    ability = getattr(pokemon, "ability", None)
    if item and not isinstance(item, str):
        item = getattr(item, "name", str(item))
    if ability and not isinstance(ability, str):
        ability = getattr(ability, "name", str(ability))
    return {
        "species": str(getattr(pokemon, "species", getattr(pokemon, "name", ""))),
        "hp": int(getattr(pokemon, "hp", 0) or 0),
        "maxhp": int(getattr(pokemon, "max_hp", getattr(pokemon, "maxhp", 0)) or 0),
        "status": str(getattr(pokemon, "status", "") or ""),
        "ability": _normalized_key(str(ability or "")),
        "item": _normalized_key(str(item or "")),
        "fainted": bool(getattr(pokemon, "is_fainted", False) or getattr(pokemon, "hp", 0) <= 0),
        "boosts": _canonical_boosts(getattr(pokemon, "boosts", {}) or {}),
        "volatiles": sorted(str(key) for key in (getattr(pokemon, "volatiles", {}) or {}).keys()),
    }


def _snapshot_battle(battle, turn_index: int) -> Dict[str, Any]:
    sides = []
    for index, participant in enumerate(battle.participants[:2], start=1):
        active = list(getattr(participant, "active", []))
        if not active and not any(getattr(poke, "hp", 0) > 0 for poke in getattr(participant, "pokemons", [])):
            active = list(getattr(participant, "pokemons", []))[: getattr(participant, "max_active", 1)]
        side = getattr(participant, "side", None)
        condition_names = set(str(key) for key in getattr(side, "conditions", {}).keys())
        hazard_name_map = {
            "rocks": "stealthrock",
            "stealthrock": "stealthrock",
            "spikes": "spikes",
            "toxicspikes": "toxicspikes",
            "stickyweb": "stickyweb",
            "steelsurge": "gmaxsteelsurge",
            "gmaxsteelsurge": "gmaxsteelsurge",
        }
        for key, value in getattr(side, "hazards", {}).items():
            if value:
                condition_names.add(hazard_name_map.get(str(key), str(key)))
        sides.append(
            {
                "name": f"p{index}",
                "active": [_snapshot_pokemon(poke) for poke in active],
                "side_conditions": sorted(condition_names),
            }
        )

    field = getattr(battle, "field", None)
    return {
        "turn": turn_index,
        "sides": sides,
        "weather": str(getattr(field, "weather", "") or "") if field else "",
        "terrain": str(getattr(field, "terrain", "") or "") if field else "",
        "pseudo_weather": sorted(str(key) for key in getattr(field, "pseudo_weather", {}).keys()) if field else [],
    }


def _parse_choice(choice: str, participant, battle, movedex: Dict[str, Any], modules: Dict[str, Any]):
    Action = __import__("pokemon.battle.actions", fromlist=["Action"]).Action
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType

    text = str(choice or "").strip()
    if not text:
        raise ValueError("Empty choice is not supported in differential tests")
    if text.lower().startswith("switch "):
        selected = text[7:].strip()
        replacement = None
        if selected.isdigit():
            index = int(selected) - 1
            all_pokemon = list(getattr(participant, "pokemons", []))
            if index < 0 or index >= len(all_pokemon):
                raise IndexError(f"Switch index {selected} is out of range for {participant.name}")
            replacement = all_pokemon[index]
        else:
            wanted = _normalized_key(selected)
            for candidate in getattr(participant, "pokemons", []):
                if _normalized_key(getattr(candidate, "species", getattr(candidate, "name", ""))) == wanted:
                    replacement = candidate
                    break
        if replacement is None:
            raise KeyError(f"Switch target {selected!r} not found for {participant.name}")
        if replacement in getattr(participant, "active", []):
            raise ValueError(f"Switch target {selected!r} is already active for {participant.name}")
        if getattr(replacement, "hp", 0) <= 0:
            raise ValueError(f"Switch target {selected!r} is fainted for {participant.name}")
        return Action(actor=participant, action_type=ActionType.SWITCH, pokemon=replacement, priority=6)
    if not text.lower().startswith("move "):
        raise ValueError(f"Unsupported differential choice: {choice}")

    selected = text[5:].strip()
    user = participant.active[0]
    move_slot = None
    if selected.isdigit():
        index = int(selected) - 1
        if index < 0 or index >= len(getattr(user, "moves", []) or []):
            raise IndexError(f"Move index {selected} is out of range for {user.name}")
        move_slot = user.moves[index]
    else:
        wanted = _normalized_key(selected)
        for candidate in getattr(user, "moves", []) or []:
            candidate_key = getattr(candidate, "key", None) or _normalized_key(getattr(candidate, "name", ""))
            if candidate_key == wanted:
                move_slot = candidate
                break
        if move_slot is None:
            raise KeyError(f"Move {selected!r} not found for {user.name}")

    battle_move = _build_battle_move(getattr(move_slot, "name", selected), movedex, modules)
    if (battle_move.raw or {}).get("target") == "self":
        target = participant
    else:
        opponents = battle.opponents_of(participant)
        target = opponents[0] if opponents else None
    return Action(actor=participant, action_type=ActionType.MOVE, target=target, move=battle_move, pokemon=user)


def run_fusion_scenario(scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
    battle, movedex, modules = _build_battle_from_scenario(scenario)
    snapshots = [_snapshot_battle(battle, 0)]

    def _is_switch_action(action) -> bool:
        action_type = getattr(action, "action_type", None)
        if action_type is ActionType.SWITCH:
            return True
        return getattr(action_type, "name", None) == "SWITCH"

    for side, choice in (scenario.get("setup_post") or {}).items():
        participant_index = 0 if side == "p1" else 1
        participant = battle.participants[participant_index]
        try:
            post_action = _parse_choice(choice, participant, battle, movedex, modules)
        except ValueError as exc:
            if "already active" in str(exc):
                continue
            raise
        if _is_switch_action(post_action):
            battle.perform_switch_action(participant, post_action.pokemon)
    if scenario.get("setup_post"):
        snapshots.append(_snapshot_battle(battle, 1))

    turn_base = len(snapshots) - 1
    for turn_index, turn in enumerate(scenario.get("turns", []), start=1):
        actions = []
        for participant, side in zip(battle.participants[:2], ("p1", "p2")):
            actions.append(_parse_choice(turn[side], participant, battle, movedex, modules))
        battle.execute_turn(actions)
        battle.end_turn()
        for side, choice in (turn.get("post") or {}).items():
            participant_index = 0 if side == "p1" else 1
            participant = battle.participants[participant_index]
            try:
                post_action = _parse_choice(choice, participant, battle, movedex, modules)
            except ValueError as exc:
                if "already active" in str(exc):
                    continue
                raise
            if _is_switch_action(post_action):
                battle.perform_switch_action(participant, post_action.pokemon)
        snapshots.append(_snapshot_battle(battle, turn_base + turn_index))

    return snapshots


def run_showdown_scenario(scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
    process = subprocess.run(
        ["node", str(SHOWDOWN_RUNNER), str(SHOWDOWN_ROOT)],
        input=json.dumps(scenario),
        text=True,
        capture_output=True,
        cwd=str(ROOT),
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(
            "Showdown differential runner failed:\n"
            f"STDOUT:\n{process.stdout}\n"
            f"STDERR:\n{process.stderr}"
        )
    return json.loads(process.stdout)


__all__ = ["run_fusion_scenario", "run_showdown_scenario"]
