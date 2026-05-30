"""Tests for Showdown-style event primitives in the Python battle engine."""

from __future__ import annotations

from .helpers import build_battle


class _AbilityGate:
    def call(self, func: str, *args, **kwargs):
        if func == "onSetStatus":
            return False
        return None


class _AbilityAfterStatus:
    def __init__(self):
        self.after = 0

    def call(self, func: str, *args, **kwargs):
        if func == "onAfterSetStatus":
            self.after += 1
        return None


class _AbilityVolatileGate:
    def call(self, func: str, *args, **kwargs):
        if func == "onTryAddVolatile":
            return False
        return None


class _AbilitySwap:
    def __init__(self, name: str):
        self.name = name
        self.raw = {}
        self.end_calls = 0
        self.start_calls = 0

    def onEnd(self, *args, **kwargs):
        self.end_calls += 1
        return True

    def onStart(self, *args, **kwargs):
        self.start_calls += 1
        return True


def test_run_event_blocks_set_status_from_target_ability():
    battle, attacker, defender = build_battle()
    defender.ability = _AbilityGate()

    applied = battle.apply_status_condition(
        defender,
        "brn",
        source=attacker,
        effect="move:willowisp",
    )

    assert applied is False
    assert defender.status == 0


def test_set_status_runs_after_set_status_event():
    battle, attacker, defender = build_battle()
    defender.ability = _AbilityAfterStatus()

    applied = defender.setStatus(
        "par",
        source=attacker,
        battle=battle,
        effect="move:thunderwave",
    )

    assert applied is True
    assert defender.status == "par"
    assert defender.ability.after == 1


def test_add_volatile_runs_try_add_volatile_gate():
    battle, attacker, defender = build_battle()
    defender.ability = _AbilityVolatileGate()

    added = battle.add_volatile(defender, "taunt", source=attacker, effect="move:taunt")

    assert added is False
    assert "taunt" not in defender.volatiles


def test_set_ability_runs_end_and_start_events():
    battle, attacker, _ = build_battle()
    old_ability = _AbilitySwap("oldability")
    new_ability = _AbilitySwap("newability")
    attacker.ability = old_ability
    attacker.ability_state = battle.init_effect_state(old_ability, target=attacker)

    previous = battle.set_ability(attacker, new_ability, source=attacker)

    assert previous is old_ability
    assert attacker.ability is new_ability
    assert old_ability.end_calls == 1
    assert new_ability.start_calls == 1


def test_add_volatile_runs_condition_handler_start():
    battle, attacker, defender = build_battle()

    added = battle.add_volatile(defender, "stall", source=attacker, effect="move:protect")

    assert added is True
    assert defender.volatiles.get("stall", {}).get("counter") == 1


def test_add_volatile_restart_uses_condition_handler():
    battle, attacker, defender = build_battle()
    defender.volatiles["stall"] = {"counter": 8}

    restarted = battle.add_volatile(defender, "stall", source=attacker, effect="move:protect")

    assert restarted is True
    assert defender.volatiles.get("stall", {}).get("counter") == 1
