import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import (
    Action,
    ActionType,
    Battle,
    BattleMove,
    BattleParticipant,
    BattleType,
)
from pokemon.data.text import DEFAULT_TEXT
from pokemon.dex.entities import Stats


def _run_move(move_raw, user_boosts=None, target_boosts=None, power: int = 0):
    user = Pokemon("User", level=1, hp=100, max_hp=100)
    target = Pokemon("Target", level=1, hp=100, max_hp=100)
    base = Stats(
        hp=100,
        attack=50,
        defense=50,
        special_attack=50,
        special_defense=50,
        speed=50,
    )
    user.base_stats = base
    target.base_stats = base
    if user_boosts:
        user.boosts = user_boosts
    if target_boosts:
        target.boosts = target_boosts
    part1 = BattleParticipant("P1", [user])
    part2 = BattleParticipant("P2", [target])
    part1.active = [user]
    part2.active = [target]
    battle = Battle(BattleType.WILD, [part1, part2])
    logs: list[str] = []
    battle.log_action = logs.append
    move = BattleMove(
        "TestMove",
        power=power,
        accuracy=True,
        raw=move_raw,
    )
    action = Action(part1, ActionType.MOVE, part2, move, priority=0, pokemon=user)
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


def test_secondary_debuff_message_on_hit():
    move_raw = {
        "category": "Physical",
        "target": "normal",
        "secondary": {"chance": 100, "boosts": {"def": -1}},
    }
    logs = _run_move(move_raw, power=50)
    expected = (
        DEFAULT_TEXT["default"]["unboost"]
        .replace("[POKEMON]", "Target")
        .replace("[STAT]", DEFAULT_TEXT["def"]["statName"])
    )
    assert expected in logs


def test_no_message_when_secondary_fails_with_damage():
    move_raw = {
        "category": "Physical",
        "target": "normal",
        "secondary": {"chance": 100, "boosts": {"def": -1}},
    }
    logs = _run_move(move_raw, target_boosts={"defense": -6}, power=50)
    expected = (
        DEFAULT_TEXT["default"]["unboost"]
        .replace("[POKEMON]", "Target")
        .replace("[STAT]", DEFAULT_TEXT["def"]["statName"])
    )
    fail_expected = (
        DEFAULT_TEXT["default"]["unboost0"]
        .replace("[POKEMON]", "Target")
        .replace("[STAT]", DEFAULT_TEXT["def"]["statName"])
    )
    assert expected not in logs
    assert fail_expected not in logs
