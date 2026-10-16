"""Shared helpers for status tests."""

from __future__ import annotations

import importlib
import os
import random
import sys
from typing import Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
        sys.path.insert(0, ROOT)


def load_modules():
        """Use the active import context without replacing module identities.

        Pytest restores each module's imports around legacy stub-based tests.
        Normal imports follow that context; an extra cache or file-based reload
        leaves battle classes and monkeypatched effect handlers out of sync.
        """
        battledata = importlib.import_module("pokemon.battle.battledata")
        engine = importlib.import_module("pokemon.battle.engine")
        damage_mod = importlib.import_module("pokemon.battle.damage")
        entities = importlib.import_module("pokemon.dex.entities")
        items_funcs = importlib.import_module("pokemon.dex.functions.items_funcs")
        return {
                "Pokemon": battledata.Pokemon,
                "Battle": engine.Battle,
                "BattleParticipant": engine.BattleParticipant,
                "BattleType": engine.BattleType,
                "Move": battledata.Move,
                "BattleMove": engine.BattleMove,
                "Stats": entities.Stats,
                "damage_calc": damage_mod.damage_calc,
                "FlameOrb": items_funcs.Flameorb,
        }


def make_stats(value: int = 120):
        modules = load_modules()
        Stats = modules["Stats"]
        return Stats(hp=value, attack=value, defense=value, special_attack=value, special_defense=value, speed=value)


def build_battle(
        *,
        attacker_status=None,
        defender_status=None,
        attacker_ability=None,
        defender_ability=None,
        attacker_types=None,
        defender_types=None,
) -> Tuple:
        modules = load_modules()
        Pokemon = modules["Pokemon"]
        Battle = modules["Battle"]
        BattleParticipant = modules["BattleParticipant"]
        BattleType = modules["BattleType"]

        attacker = Pokemon("Attacker", level=50, hp=200, max_hp=200)
        defender = Pokemon("Defender", level=50, hp=200, max_hp=200)

        for mon, ability, types in (
                (attacker, attacker_ability, attacker_types),
                (defender, defender_ability, defender_types),
        ):
                mon.base_stats = make_stats()
                mon.types = types or ["Normal"]
                mon.boosts = {
                        "attack": 0,
                        "defense": 0,
                        "special_attack": 0,
                        "special_defense": 0,
                        "speed": 0,
                        "accuracy": 0,
                        "evasion": 0,
                }
                if ability:
                        mon.ability = ability

        if attacker_status:
                attacker.setStatus(attacker_status, source=attacker)
        if defender_status:
                defender.setStatus(defender_status, source=defender)

        part1 = BattleParticipant("P1", [attacker])
        part2 = BattleParticipant("P2", [defender])
        part1.active = [attacker]
        part2.active = [defender]

        battle = Battle(BattleType.WILD, [part1, part2])
        attacker.battle = battle
        defender.battle = battle
        return battle, attacker, defender


def physical_move(name: str = "Tackle", power: int = 70, move_type: str = "Normal", category: str = "Physical"):
        modules = load_modules()
        Move = modules["Move"]
        move = Move(name)
        move.power = power
        move.type = move_type
        move.category = category
        move.accuracy = 100
        move.raw = {
                "name": name,
                "basePower": power,
                "type": move_type,
                "category": category,
                "accuracy": 100,
        }
        move.key = name.lower()
        return move


def battle_move(
        name: str = "Tackle",
        power: int = 70,
        move_type: str = "Normal",
        category: str = "Physical",
        *,
        accuracy: int | float | bool = 100,
        priority: int = 0,
        flags: dict | None = None,
        raw: dict | None = None,
):
        """Return a fully initialized ``BattleMove`` for engine-level tests."""

        modules = load_modules()
        BattleMove = modules["BattleMove"]
        move_raw = {
                "name": name,
                "basePower": power,
                "type": move_type,
                "category": category,
                "accuracy": accuracy,
                "priority": priority,
                "flags": dict(flags or {}),
        }
        if raw:
                move_raw.update(raw)
        return BattleMove(
                name=name,
                key=name.lower(),
                power=power,
                type=move_type,
                accuracy=accuracy,
                priority=priority,
                raw=move_raw,
        )


def run_damage(attacker, defender, move):
        modules = load_modules()
        damage_calc = modules["damage_calc"]
        rng = random.Random(0)
        result = damage_calc(attacker, defender, move, battle=None, rng=rng)
        return result.debug.get("damage", [0])[0]


def make_flame_orb():
        modules = load_modules()
        return modules["FlameOrb"]()


def resolve_status_text(status: str, event: str) -> str | None:
        """Return the text template for ``status`` and ``event``."""

        try:
                from pokemon.data.text import DEFAULT_TEXT  # type: ignore
        except Exception:  # pragma: no cover - fallback when data missing
                return None

        key = status
        visited: set[str] = set()
        while key:
                entry = DEFAULT_TEXT.get(key, {})
                template = entry.get(event)
                if template is None:
                        return None
                if isinstance(template, str) and template.startswith("#"):
                        ref = template[1:]
                        if not ref or ref in visited:
                                return None
                        visited.add(ref)
                        key = ref
                        continue
                return template
        return None
