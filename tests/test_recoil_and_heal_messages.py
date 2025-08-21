"""Tests for recoil, drain and healing announcements."""

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


def _run_move(move_raw, *, power: int = 0, user_hp: int = 100, target_hp: int = 100):
    """Run ``move_raw`` in a simple battle and capture log output."""
    user = Pokemon("User", level=1, hp=user_hp, max_hp=100)
    target = Pokemon("Target", level=1, hp=target_hp, max_hp=100)
    base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    user.base_stats = base
    target.base_stats = base
    part1 = BattleParticipant("P1", [user], is_ai=False)
    part2 = BattleParticipant("P2", [target], is_ai=False)
    part1.active = [user]
    part2.active = [target]
    battle = Battle(BattleType.WILD, [part1, part2])
    logs = []
    battle.log_action = logs.append
    move = BattleMove("TestMove", power=power, accuracy=True, raw=move_raw)
    target_part = part1 if move_raw.get("target") in {"self", "allies", "ally"} else part2
    action = Action(part1, ActionType.MOVE, target_part, move, priority=0, pokemon=user)
    battle.use_move(action)
    return logs


def test_drain_move_logs_messages():
    move_raw = {"category": "Physical", "target": "normal", "drain": [1, 2]}
    logs = _run_move(move_raw, power=50, user_hp=50)
    drain_msg = DEFAULT_TEXT["drain"]["heal"].replace("[SOURCE]", "Target")
    heal_msg = DEFAULT_TEXT["default"]["heal"].replace("[POKEMON]", "User")
    assert drain_msg in logs
    assert heal_msg in logs


def test_recoil_move_logs_message():
    move_raw = {"category": "Physical", "target": "normal", "recoil": [1, 2]}
    logs = _run_move(move_raw, power=50)
    recoil_msg = DEFAULT_TEXT["recoil"]["damage"].replace("[POKEMON]", "User")
    assert recoil_msg in logs


def test_flat_heal_move_logs_message():
    move_raw = {"category": "Status", "target": "self", "heal": [1, 2]}
    logs = _run_move(move_raw, user_hp=50)
    heal_msg = DEFAULT_TEXT["default"]["heal"].replace("[POKEMON]", "User")
    assert heal_msg in logs
