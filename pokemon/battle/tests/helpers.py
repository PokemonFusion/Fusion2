"""Shared helpers for status tests."""

from __future__ import annotations

import importlib.util
import os
import random
import sys
import types
from typing import Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

battle_pkg = types.ModuleType("pokemon.battle")
battle_pkg.__path__ = []  # type: ignore[attr-defined]
sys.modules.setdefault("pokemon.battle", battle_pkg)

_MODULES = {}


def _load_module(name: str, relative_path: str):
        path = os.path.join(ROOT, relative_path)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module


def load_modules():
        """Ensure the lightweight battle modules are loaded for tests."""

        if _MODULES:
                return _MODULES

        # Core battle modules
        battledata = _load_module("pokemon.battle.battledata", "pokemon/battle/battledata.py")
        engine = _load_module("pokemon.battle.engine", "pokemon/battle/engine.py")
        damage_mod = _load_module("pokemon.battle.damage", "pokemon/battle/damage.py")

        # Status package
        _load_module("pokemon.battle.status.status_core", "pokemon/battle/status/status_core.py")
        _load_module("pokemon.battle.status.burn", "pokemon/battle/status/burn.py")
        _load_module("pokemon.battle.status.poison", "pokemon/battle/status/poison.py")
        _load_module("pokemon.battle.status.paralysis", "pokemon/battle/status/paralysis.py")
        _load_module("pokemon.battle.status.sleep", "pokemon/battle/status/sleep.py")
        _load_module("pokemon.battle.status.freeze", "pokemon/battle/status/freeze.py")
        _load_module("pokemon.battle.status", "pokemon/battle/status/__init__.py")

        # Supporting dex modules
        entities = _load_module("pokemon.dex.entities", "pokemon/dex/entities.py")
        items_funcs = _load_module("pokemon.dex.functions.items_funcs", "pokemon/dex/functions/items_funcs.py")
        _load_module("pokemon.dex.functions.conditions_funcs", "pokemon/dex/functions/conditions_funcs.py")

        _MODULES.update(
                {
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
        )
        return _MODULES


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


def run_damage(attacker, defender, move):
        modules = load_modules()
        damage_calc = modules["damage_calc"]
        rng = random.Random(0)
        result = damage_calc(attacker, defender, move, battle=None, rng=rng)
        return result.debug.get("damage", [0])[0]


def make_flame_orb():
        modules = load_modules()
        return modules["FlameOrb"]()
