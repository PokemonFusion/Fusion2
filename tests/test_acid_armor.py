"""Tests for the move Acid Armor."""

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


def test_acid_armor_boosts_defense_by_two():
    """Acid Armor should increase the user's Defense by exactly two stages."""
    user = Pokemon("User", level=1, hp=100, max_hp=100)
    target = Pokemon("Target", level=1, hp=100, max_hp=100)
    part1 = BattleParticipant("P1", [user])
    part2 = BattleParticipant("P2", [target])
    part1.active = [user]
    part2.active = [target]
    battle = Battle(BattleType.WILD, [part1, part2])
    move = BattleMove(
        "Acid Armor",
        power=0,
        accuracy=True,
        raw={"category": "Status", "target": "self", "boosts": {"def": 2}},
    )
    move.execute(user, target, battle)
    assert user.boosts["defense"] == 2


def test_acid_armor_logs_successful_use():
    """Using Acid Armor should log success instead of no effect."""
    user = Pokemon("User", level=1, hp=100, max_hp=100)
    target = Pokemon("Target", level=1, hp=100, max_hp=100)
    part1 = BattleParticipant("P1", [user])
    part2 = BattleParticipant("P2", [target])
    part1.active = [user]
    part2.active = [target]
    battle = Battle(BattleType.WILD, [part1, part2])
    logs: list[str] = []
    battle.log_action = lambda msg: logs.append(msg)
    move = BattleMove(
        "Acid Armor",
        power=0,
        accuracy=True,
        raw={"category": "Status", "target": "self", "boosts": {"def": 2}},
    )
    action = Action(part1, ActionType.MOVE, part1, move, priority=0, pokemon=user)
    battle.use_move(action)
    joined = " ".join(logs)
    assert "had no effect" not in joined and "failed" not in joined
    assert any("User used Acid Armor" in msg for msg in logs)
