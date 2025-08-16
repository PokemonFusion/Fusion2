"""Tests for moves that require double battles (2v2)."""

import importlib
import os
import sys
import pytest

from tests.test_move_effects import setup_env, setup_battle

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


@pytest.fixture
def env():
    """Provide battle environment including move functions."""
    data = setup_env()
    mv_mod = importlib.import_module("pokemon.dex.functions.moves_funcs")
    data["moves_mod"] = mv_mod
    yield data
    for mod in [
        "pokemon.battle",
        "pokemon.battle.utils",
        "pokemon.battle.battledata",
        "pokemon.battle.engine",
        "pokemon.dex",
        "pokemon.dex.entities",
        "pokemon.dex.functions.moves_funcs",
    ]:
        sys.modules.pop(mod, None)


def setup_double_battle(env):
    """Create a simple 2v2 battle."""
    Pokemon = env["Pokemon"]
    BattleParticipant = env["BattleParticipant"]
    Battle = env["Battle"]
    BattleType = env["BattleType"]

    a1 = Pokemon("A1")
    a2 = Pokemon("A2")
    b1 = Pokemon("B1")
    b2 = Pokemon("B2")

    p1 = BattleParticipant("P1", [a1, a2], is_ai=False, max_active=2)
    p2 = BattleParticipant("P2", [b1, b2], is_ai=False, max_active=2)
    p1.active = [a1, a2]
    p2.active = [b1, b2]
    p1.side.active = p1.active
    p2.side.active = p2.active
    battle = Battle(BattleType.WILD, [p1, p2])
    return battle, p1, p2, a1, a2, b1, b2


def test_allyswitch_requires_double_battle(env):
    """Ally Switch fails in singles and swaps positions in doubles."""
    mv_mod = env["moves_mod"]

    # Single battle should fail
    battle, p1, p2, user, target = setup_battle(env)
    assert mv_mod.Allyswitch().onHit(user, target, battle) is False

    # Double battle should swap active Pokemon
    battle2, p1d, p2d, first, second, foe1, _ = setup_double_battle(env)
    move = env["BattleMove"](
        "Ally Switch",
        power=0,
        accuracy=True,
        onHit=mv_mod.Allyswitch().onHit,
        raw={"category": "Status", "target": "self"},
    )
    action = env["Action"](p1d, env["ActionType"].MOVE, p1d, move, move.priority, pokemon=first)
    p1d.pending_action = [action]
    battle2.run_turn()
    assert p1d.active == [second, first]


def test_follow_me_requires_multi_battle(env):
    """Follow Me can only be used when multiple Pokemon are active."""
    mv_mod = env["moves_mod"]
    move = env["BattleMove"]("Follow Me", power=0, accuracy=True, raw={"category": "Status"})

    # Single battle should not allow Follow Me
    battle, p1, p2, user, target = setup_battle(env)
    assert mv_mod.Followme().onTry(user, target, move, battle=battle) is False

    # Double battle should allow Follow Me
    battle2, p1d, p2d, user2, ally2, foe2, _ = setup_double_battle(env)
    assert mv_mod.Followme().onTry(user2, foe2, move, battle=battle2) is True
