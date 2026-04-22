"""Tests for Showdown-style damage-resolution events."""

from __future__ import annotations

import random

from .helpers import build_battle, load_modules, physical_move


class _AccuracyZeroAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onAccuracy":
            return 0
        return None


class _DoubleDefenseAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onModifyDef":
            return args[0] * 2
        return None


class _NeutralizeEffectivenessAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onEffectiveness":
            return 1.0
        return None


class _ImmuneAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onImmunity":
            return False
        return None


class _NoCritAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onCriticalHit":
            return False
        return None


class _PlainAnyDamageAbility:
    def onAnyDamage(self, damage, target=None, source=None, effect=None):
        return max(1, damage // 2)


class _PlainZeroDamageAbility:
    def onDamage(self, damage, target=None, source=None, effect=None):
        return 0


def _damage_calc(attacker, defender, move, battle):
    modules = load_modules()
    rng = random.Random(0)
    return modules["damage_calc"](attacker, defender, move, battle=battle, rng=rng)


def test_accuracy_event_can_force_a_miss():
    battle, attacker, defender = build_battle(defender_ability=_AccuracyZeroAbility())
    move = physical_move(name="Tackle", power=40)

    result = _damage_calc(attacker, defender, move, battle)

    assert result.text[-1] == "Attacker uses Tackle but it missed!"
    assert result.debug.get("damage", []) == []


def test_modify_def_event_changes_defense_stat_used_in_damage():
    battle, attacker, defender = build_battle()
    move = physical_move(name="Tackle", power=70)

    baseline = _damage_calc(attacker, defender, move, battle)
    baseline_damage = baseline.debug["damage"][0]

    defender.ability = _DoubleDefenseAbility()
    modified = _damage_calc(attacker, defender, move, battle)

    assert modified.debug["defense"][0] == baseline.debug["defense"][0] * 2
    assert modified.debug["damage"][0] < baseline_damage


def test_effectiveness_event_can_override_type_multiplier():
    battle, attacker, defender = build_battle(defender_types=["Grass"], defender_ability=_NeutralizeEffectivenessAbility())
    move = physical_move(name="Flame Wheel", power=60, move_type="Fire")

    result = _damage_calc(attacker, defender, move, battle)

    assert result.debug["type_effectiveness"][0] == 1.0
    assert DEFAULT_TEXT_FRAGMENT("super", result.text) is False


def test_immunity_event_can_block_damage():
    battle, attacker, defender = build_battle(defender_ability=_ImmuneAbility())
    move = physical_move(name="Tackle", power=40)

    result = _damage_calc(attacker, defender, move, battle)

    assert result.debug["type_effectiveness"][0] == 0
    assert DEFAULT_TEXT_FRAGMENT("immune", result.text) is True
    assert result.debug.get("damage", []) == []


def test_critical_hit_event_can_cancel_forced_crit():
    battle, attacker, defender = build_battle(defender_ability=_NoCritAbility())
    move = physical_move(name="Slash", power=70)
    move.raw["willCrit"] = True

    result = _damage_calc(attacker, defender, move, battle)

    assert result.debug["critical"][0] is False


def test_plain_any_damage_handler_can_modify_damage():
    battle, attacker, defender = build_battle()
    battle.participants[0].active[0].ability = _PlainAnyDamageAbility()
    move = physical_move(name="Tackle", power=70)

    modified = _damage_calc(attacker, defender, move, battle)

    baseline_battle, baseline_attacker, baseline_defender = build_battle()
    baseline = _damage_calc(baseline_attacker, baseline_defender, move, baseline_battle)

    assert modified.debug["damage"][0] < baseline.debug["damage"][0]


def test_plain_on_damage_handler_can_zero_damage():
    battle, attacker, defender = build_battle(defender_ability=_PlainZeroDamageAbility())
    move = physical_move(name="Tackle", power=70)

    result = _damage_calc(attacker, defender, move, battle)

    assert result.debug["damage"][0] == 0


def DEFAULT_TEXT_FRAGMENT(kind: str, text: list[str]) -> bool:
    joined = " ".join(text).lower()
    if kind == "super":
        return "super effective" in joined
    if kind == "immune":
        return "doesn't affect" in joined or "doesnt affect" in joined
    return False
