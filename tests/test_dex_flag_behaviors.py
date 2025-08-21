"""Data driven tests verifying behaviour of flagged moves from the Pokédex."""

import os
import sys
from typing import List

import pytest

# Ensure repository root is on the path for direct imports when running tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

pytestmark = pytest.mark.dex

from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import (
    Action,
    ActionType,
    Battle,
    BattleMove,
    BattleParticipant,
    BattleType,
)
from pokemon.dex import MOVEDEX
from pokemon.dex.entities import Stats
from pokemon.dex.flag_groups import get_move_flag_groups

FLAG_GROUPS = get_move_flag_groups()


def _simple_heal_moves() -> List[str]:
    moves: List[str] = []
    for name in FLAG_GROUPS.get("heal", []):
        entry = MOVEDEX[name.lower()]
        raw = entry.raw
        if name.lower() == "matchagotcha":
            continue
        if (raw.get("heal") or raw.get("drain")) and not any(
            k in raw
            for k in ("onHit", "onTry", "self", "condition", "sideCondition", "slotCondition", "volatileStatus")
        ):
            moves.append(name)
    return moves


def _simple_snatch_moves() -> List[str]:
    moves: List[str] = []
    for name in FLAG_GROUPS.get("snatch", []):
        entry = MOVEDEX[name.lower()]
        raw = entry.raw
        if raw.get("target") == "self" and not any(
            k in raw for k in ("onHit", "onTry", "condition", "self", "volatileStatus")
        ):
            moves.append(name)
    return moves


HEAL_MOVES = _simple_heal_moves()
SNATCH_MOVES = _simple_snatch_moves()


@pytest.mark.parametrize("move_name", HEAL_MOVES)
def test_heal_moves_restore_hp(move_name: str) -> None:
    """Moves flagged with ``heal`` should recover HP for some target."""

    entry = MOVEDEX[move_name.lower()]
    move = BattleMove(move_name, priority=entry.raw.get("priority", 0), pp=5)

    user = Pokemon("User")
    target = Pokemon("Target")
    base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    for poke in (user, target):
        poke.base_stats = base
        poke.hp = poke.max_hp = 100
        poke.types = ["Normal"]

    user.hp = 50
    target.hp = 100

    p1 = BattleParticipant("P1", [user], is_ai=False)
    p2 = BattleParticipant("P2", [target], is_ai=False)
    p1.active = [user]
    p2.active = [target]

    target_part = p1 if entry.raw.get("target") in {"self", "allies", "ally"} else p2
    action = Action(p1, ActionType.MOVE, target_part, move, priority=move.priority)
    p1.pending_action = action

    battle = Battle(BattleType.WILD, [p1, p2])
    logs: List[str] = []
    battle.log_action = logs.append
    battle.start_turn()
    battle.run_switch()
    battle.run_after_switch()
    battle.run_move()
    battle.run_faint()
    battle.residual()
    battle.end_turn()

    assert user.hp > 50 or target.hp > 100


@pytest.mark.parametrize("move_name", SNATCH_MOVES)
def test_snatchable_moves_are_intercepted(move_name: str) -> None:
    """Moves with the ``snatch`` flag should be stolen by an opposing Snatch."""

    entry = MOVEDEX[move_name.lower()]
    move = BattleMove(move_name, priority=entry.raw.get("priority", 0), pp=5)

    snatcher = Pokemon("Snatcher")
    user = Pokemon("User")
    base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    for poke in (snatcher, user):
        poke.base_stats = base
        poke.hp = poke.max_hp = 100
        poke.types = ["Normal"]
        poke.boosts = {
            "attack": 0,
            "defense": 0,
            "special_attack": 0,
            "special_defense": 0,
            "speed": 0,
            "accuracy": 0,
            "evasion": 0,
        }
        poke.volatiles = {}
    snatcher.hp = 50

    p1 = BattleParticipant("P1", [snatcher], is_ai=False)
    p2 = BattleParticipant("P2", [user], is_ai=False)
    p1.active = [snatcher]
    p2.active = [user]

    snatch_entry = MOVEDEX["snatch"]
    snatch_move = BattleMove("Snatch", priority=snatch_entry.raw.get("priority", 0), pp=5)

    action1 = Action(p1, ActionType.MOVE, p1, snatch_move, priority=snatch_move.priority)
    action2 = Action(p2, ActionType.MOVE, p2, move, priority=move.priority)
    p1.pending_action = action1
    p2.pending_action = action2

    battle = Battle(BattleType.WILD, [p1, p2])
    logs: List[str] = []
    battle.log_action = logs.append
    snatch_hp = snatcher.hp
    snatch_boosts = snatcher.boosts.copy()
    user_hp = user.hp
    user_boosts = user.boosts.copy()

    battle.start_turn()
    battle.run_switch()
    battle.run_after_switch()
    battle.run_move()
    battle.run_faint()
    battle.residual()
    battle.end_turn()

    log_text = " ".join(logs).lower()
    changed = snatcher.hp > snatch_hp or snatcher.boosts != snatch_boosts
    unchanged = user.hp == user_hp and user.boosts == user_boosts

    assert "snatched" in log_text and changed and unchanged
