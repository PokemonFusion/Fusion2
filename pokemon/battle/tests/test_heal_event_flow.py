"""Tests for Showdown-style healing event routing."""

from __future__ import annotations

from .helpers import build_battle, load_modules


class _BlockHealAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onTryHeal":
            return False
        return None


class _BoostSourceHealAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onSourceTryHeal":
            return int(args[0]) * 2
        return None


def test_try_heal_event_can_block_direct_healing():
    battle, attacker, defender = build_battle(defender_ability=_BlockHealAbility())
    defender.max_hp = 200
    defender.hp = 100

    applied = battle.heal(defender, 50, source=attacker, effect="move:recover")

    assert applied == 0
    assert defender.hp == 100


def test_source_try_heal_event_scales_drain_healing():
    modules = load_modules()
    battle, attacker, defender = build_battle(defender_ability=_BoostSourceHealAbility())
    attacker.max_hp = 200
    attacker.hp = 100
    defender.hp = 200
    move = modules["BattleMove"](
        name="Absorb",
        power=40,
        accuracy=100,
        type="Grass",
        raw={"category": "Physical", "basePower": 40, "accuracy": 100, "drain": [1, 2]},
    )
    move.key = "absorb"
    baseline_battle, baseline_attacker, baseline_defender = build_battle()
    baseline_attacker.max_hp = 200
    baseline_attacker.hp = 100
    baseline_defender.hp = 200
    baseline_move = modules["BattleMove"](
        name="Absorb",
        power=40,
        accuracy=100,
        type="Grass",
        raw={"category": "Physical", "basePower": 40, "accuracy": 100, "drain": [1, 2]},
    )
    baseline_move.key = "absorb"

    baseline_move.execute(baseline_attacker, baseline_defender, baseline_battle)

    move.execute(attacker, defender, battle)

    assert attacker.hp > baseline_attacker.hp


def test_liquid_ooze_reverses_drain_healing_with_real_dex_handler():
    modules = load_modules()
    battle, attacker, defender = build_battle(defender_ability="Liquid Ooze")
    attacker.max_hp = 200
    attacker.hp = 150
    defender.hp = 200
    move = modules["BattleMove"](
        name="Absorb",
        power=40,
        accuracy=100,
        type="Grass",
        raw={
            "category": "Physical",
            "basePower": 40,
            "accuracy": 100,
            "drain": [1, 2],
            "flags": {"drain": 1},
        },
    )
    move.key = "absorb"

    move.execute(attacker, defender, battle)

    assert attacker.hp < 150


def test_big_root_real_item_name_scales_drain_healing():
    modules = load_modules()
    battle, attacker, defender = build_battle()
    attacker.item = "Big Root"
    attacker.max_hp = 200
    attacker.hp = 100
    defender.hp = 200
    move = modules["BattleMove"](
        name="Absorb",
        power=40,
        accuracy=100,
        type="Grass",
        raw={
            "category": "Physical",
            "basePower": 40,
            "accuracy": 100,
            "drain": [1, 2],
            "flags": {"drain": 1},
        },
    )
    move.key = "absorb"

    move.execute(attacker, defender, battle)

    assert attacker.hp > 109
