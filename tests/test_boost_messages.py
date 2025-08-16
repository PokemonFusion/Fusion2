import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import (
    Action,
    ActionType,
    Battle,
    BattleParticipant,
    BattleType,
    BattleMove,
)
from pokemon.data.text import DEFAULT_TEXT


def _run_move(move_raw, user_boosts=None):
    user = Pokemon("User", level=1, hp=100, max_hp=100)
    target = Pokemon("Target", level=1, hp=100, max_hp=100)
    if user_boosts:
        user.boosts = user_boosts
    part1 = BattleParticipant("P1", [user])
    part2 = BattleParticipant("P2", [target])
    part1.active = [user]
    part2.active = [target]
    battle = Battle(BattleType.WILD, [part1, part2])
    logs: list[str] = []
    battle.log_action = logs.append
    move = BattleMove(
        "TestMove",
        power=0,
        accuracy=True,
        raw=move_raw,
    )
    action = Action(part1, ActionType.MOVE, part1, move, priority=0, pokemon=user)
    battle.use_move(action)
    return logs


def test_boost_message_on_success():
    logs = _run_move({"category": "Status", "target": "self", "boosts": {"atk": 1}})
    expected = (
        DEFAULT_TEXT["default"]["boost"]
        .replace("[POKEMON]", "User")
        .replace("[STAT]", DEFAULT_TEXT["atk"]["statName"])
    )
    assert expected in logs


def test_boost_message_at_cap():
    logs = _run_move(
        {"category": "Status", "target": "self", "boosts": {"atk": 1}},
        user_boosts={"attack": 6},
    )
    expected = (
        DEFAULT_TEXT["default"]["boost0"]
        .replace("[POKEMON]", "User")
        .replace("[STAT]", DEFAULT_TEXT["atk"]["statName"])
    )
    assert expected in logs
