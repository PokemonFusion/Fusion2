"""Tests for move-abort and move-message callback routing."""

from __future__ import annotations

from .helpers import build_battle, load_modules


def _battle_action(actor, action_type, **kwargs):
    Action = __import__("pokemon.battle.actions", fromlist=["Action"]).Action
    return Action(actor=actor, action_type=action_type, **kwargs)


class _AbortTracker:
    def __init__(self):
        self.aborted = 0
        self.failed = 0

    def onMoveAborted(self, *args, **kwargs):
        self.aborted += 1
        return True

    def onMoveFail(self, *args, **kwargs):
        self.failed += 1
        return True


class _MessageTracker:
    def __init__(self):
        self.calls = 0

    def onUseMoveMessage(self, *args, **kwargs):
        self.calls += 1
        return True


def test_move_aborted_runs_alongside_move_fail_on_primary_hit_block():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    tracker = _AbortTracker()
    move = BattleMove(
        name="Test Move",
        power=50,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 50, "accuracy": 100},
        onMoveAborted=tracker.onMoveAborted,
        onMoveFail=tracker.onMoveFail,
    )
    move.key = "testmove"
    move.onTryPrimaryHit = lambda target, source, move=None, battle=None: False

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert tracker.aborted == 1
    assert tracker.failed == 1


def test_use_move_message_runs_for_successful_move_resolution():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    tracker = _MessageTracker()
    move = BattleMove(
        name="Tackle",
        power=50,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 50, "accuracy": 100},
        onUseMoveMessage=tracker.onUseMoveMessage,
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

    assert tracker.calls == 1
    assert defender.hp < defender.max_hp
