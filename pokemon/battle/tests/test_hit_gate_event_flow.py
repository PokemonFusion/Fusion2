"""Tests for TryImmunity and TryPrimaryHit event routing."""

from __future__ import annotations

from .helpers import build_battle, load_modules


def _battle_action(actor, action_type, **kwargs):
    modules = load_modules()
    Action = __import__("pokemon.battle.actions", fromlist=["Action"]).Action
    return Action(actor=actor, action_type=action_type, **kwargs)


def test_try_immunity_blocks_move_before_effect_application():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    defender.gender = "M"
    attacker.gender = "M"
    move = BattleMove(
        name="Captivate",
        power=0,
        accuracy=100,
        type="Normal",
        raw={"category": "Status", "accuracy": 100, "onTryImmunity": "Captivate.onTryImmunity", "boosts": {"spa": -2}},
    )
    move.key = "captivate"
    start_boosts = dict(defender.boosts)

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert defender.boosts == start_boosts


def test_try_primary_hit_blocks_move_on_substitute_condition():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    defender.volatiles["substitute"] = {"hp": 50}
    move = BattleMove(
        name="Some Hit Gate",
        power=40,
        accuracy=100,
        type="Dark",
        raw={"category": "Physical", "basePower": 40, "accuracy": 100, "onTryPrimaryHit": "Spitup.onTryPrimaryHit"},
    )
    move.key = "somehitgate"
    start_hp = defender.hp

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert defender.hp == start_hp


class _ReduceAnyDamageAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onAnyModifyDamage":
            return max(1, int(args[0] / 2))
        return None


class _BlockSourcePrimaryHitAbility:
    def call(self, func: str, *args, **kwargs):
        if func == "onSourceTryPrimaryHit":
            return False
        return None


def test_any_modify_damage_runs_through_event_system():
    modules = load_modules()
    damage_mod = __import__("pokemon.battle.damage", fromlist=["apply_damage"])
    battle, attacker, defender = build_battle()
    defender.ability = _ReduceAnyDamageAbility()
    move = modules["BattleMove"](
        name="Tackle",
        power=70,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 70, "accuracy": 100},
    )
    move.key = "tackle"
    baseline_battle, baseline_attacker, baseline_defender = build_battle()
    baseline_move = modules["BattleMove"](
        name="Tackle",
        power=70,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 70, "accuracy": 100},
    )
    baseline_move.key = "tackle"

    modified = damage_mod.apply_damage(attacker, defender, move, battle=battle, update_hp=False)
    baseline = damage_mod.apply_damage(
        baseline_attacker, baseline_defender, baseline_move, battle=baseline_battle, update_hp=False
    )

    assert sum(modified.debug["damage"]) < sum(baseline.debug["damage"])


def test_source_try_primary_hit_runs_for_source_owned_holders():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle(attacker_ability=_BlockSourcePrimaryHitAbility())
    move = BattleMove(
        name="Source Gate",
        power=70,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 70, "accuracy": 100},
    )
    move.key = "sourcegate"
    start_hp = defender.hp

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert defender.hp == start_hp
