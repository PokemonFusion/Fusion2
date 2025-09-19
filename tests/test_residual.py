"""Regression tests for residual damage logic."""

from __future__ import annotations

import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Provide a lightweight ``pokemon.battle`` package namespace so the engine
# modules can be imported without the full Evennia environment.
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []  # type: ignore[attr-defined]
sys.modules.setdefault("pokemon.battle", pkg_battle)

# Load battledata module
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
battledata = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = battledata
assert bd_spec.loader is not None
bd_spec.loader.exec_module(battledata)
Pokemon = battledata.Pokemon

# Load engine module
engine_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", engine_path)
eng_mod = importlib.util.module_from_spec(eng_spec)
sys.modules[eng_spec.name] = eng_mod
assert eng_spec.loader is not None
eng_spec.loader.exec_module(eng_mod)
Battle = eng_mod.Battle
BattleParticipant = eng_mod.BattleParticipant
BattleType = eng_mod.BattleType

from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS


def setup_battle(status: str):
    """Create a simple battle with ``status`` applied to the first Pokémon."""

    p1 = Pokemon("Burner", level=1, hp=80, max_hp=80)
    p1.status = status
    if status == "tox":
        p1.toxic_counter = 1
    p2 = Pokemon("Target", level=1, hp=100, max_hp=100)

    part1 = BattleParticipant("P1", [p1])
    part2 = BattleParticipant("P2", [p2])
    part1.active = [p1]
    part2.active = [p2]

    battle = Battle(BattleType.WILD, [part1, part2])
    p1.battle = battle
    p2.battle = battle
    return battle, p1, p2


def test_burn_residual_damage():
    battle, p1, _ = setup_battle("brn")
    battle.residual()
    assert p1.hp == 75


def test_poison_residual_damage():
    battle, p1, _ = setup_battle("psn")
    battle.residual()
    assert p1.hp == 70


def test_toxic_residual_increases_each_turn():
    battle, p1, _ = setup_battle("tox")
    battle.residual()
    assert p1.hp == 75
    battle.residual()
    assert p1.hp == 65


def test_toxic_converts_on_switch_out():
    p1 = Pokemon("Burner", level=1, hp=80, max_hp=80)
    p1.status = "tox"
    p1.toxic_counter = 1
    bench = Pokemon("Bench", level=1, hp=80, max_hp=80)
    target = Pokemon("Target", level=1, hp=80, max_hp=80)

    part1 = BattleParticipant("P1", [p1, bench])
    part2 = BattleParticipant("P2", [target])
    part1.active = [p1]
    part2.active = [target]

    battle = Battle(BattleType.WILD, [part1, part2])
    p1.battle = battle
    bench.battle = battle
    target.battle = battle

    handler = CONDITION_HANDLERS["tox"]
    handler.onSwitchOut(p1, battle=battle)
    assert p1.toxic_counter == 0

    part1.active = [bench]
    battle.run_after_switch()

    assert p1.status == "tox"
    assert p1.toxic_counter == 1
