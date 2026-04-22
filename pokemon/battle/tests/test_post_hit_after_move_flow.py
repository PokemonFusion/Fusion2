"""Tests for damaging-hit and after-move event routing."""

from __future__ import annotations

from .helpers import build_battle, load_modules


class _SourceDamagingHitAbility:
    def __init__(self):
        self.calls = 0

    def call(self, func: str, *args, **kwargs):
        if func == "onSourceDamagingHit":
            self.calls += 1
        return None


class _AnyAfterMoveAbility:
    def __init__(self):
        self.calls = 0

    def call(self, func: str, *args, **kwargs):
        if func == "onAnyAfterMove":
            self.calls += 1
        return None


class _AfterMoveSecondaryAbility:
    def __init__(self):
        self.calls = 0

    def call(self, func: str, *args, **kwargs):
        if func == "onAfterMoveSecondary":
            self.calls += 1
        return None


class _AfterMoveSecondarySelfAbility:
    def __init__(self):
        self.calls = 0

    def call(self, func: str, *args, **kwargs):
        if func == "onAfterMoveSecondarySelf":
            self.calls += 1
        return None


def _battle_action(actor, action_type, **kwargs):
    modules = load_modules()
    Action = __import__("pokemon.battle.actions", fromlist=["Action"]).Action
    return Action(actor=actor, action_type=action_type, **kwargs)


def test_source_damaging_hit_runs_for_attacker_after_damage():
    modules = load_modules()
    damage_mod = __import__("pokemon.battle.damage", fromlist=["apply_damage"])
    battle, attacker, defender = build_battle()
    attacker.ability = _SourceDamagingHitAbility()
    move = modules["BattleMove"](
        name="Tackle",
        power=50,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 50, "accuracy": 100},
    )
    move.key = "tackle"

    damage_mod.apply_damage(attacker, defender, move, battle=battle)

    assert attacker.ability.calls == 1


def test_any_after_move_runs_after_move_resolution():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    attacker.ability = _AnyAfterMoveAbility()
    move = BattleMove(
        name="Tackle",
        power=50,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 50, "accuracy": 100},
    )
    move.key = "tackle"

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert attacker.ability.calls == 1


def test_after_move_secondary_runs_for_target_holders():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    defender.ability = _AfterMoveSecondaryAbility()
    move = BattleMove(
        name="Tackle",
        power=50,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 50, "accuracy": 100},
    )
    move.key = "tackle"

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert defender.ability.calls == 1


def test_after_move_secondary_self_runs_for_user_holders():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    attacker.ability = _AfterMoveSecondarySelfAbility()
    move = BattleMove(
        name="Tackle",
        power=50,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 50, "accuracy": 100},
    )
    move.key = "tackle"

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert attacker.ability.calls == 1
