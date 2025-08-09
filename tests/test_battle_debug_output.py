"""Tests for battle damage debug output."""

from __future__ import annotations

import random

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from pokemon.battle.damage import apply_damage
from pokemon.battle.battledata import Pokemon
from pokemon.dex.entities import Move, Stats


class DummyBattle:
    """Minimal battle object capturing log messages."""

    def __init__(self, debug: bool = True):
        self.debug = debug
        self.logged = []
        self.field = None

    def log_action(self, message: str) -> None:
        self.logged.append(message)


def _make_pokemon(name: str) -> Pokemon:
    mon = Pokemon(name, level=50, hp=100, max_hp=100)
    mon.types = ["Normal"]
    mon.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    return mon


def _make_move() -> Move:
    return Move(
        name="Tackle",
        num=0,
        type="Normal",
        category="Physical",
        power=40,
        accuracy=100,
        pp=35,
        raw={},
    )


def test_apply_damage_logs_debug_when_enabled():
    attacker = _make_pokemon("Attacker")
    target = _make_pokemon("Target")
    move = _make_move()
    battle = DummyBattle(debug=True)
    random.seed(0)
    apply_damage(attacker, target, move, battle=battle)
    joined = " ".join(battle.logged)
    assert "[DEBUG]" in joined
    assert "atk=" in joined and "dmg=" in joined


def test_apply_damage_no_debug_when_disabled():
    attacker = _make_pokemon("Attacker")
    target = _make_pokemon("Target")
    move = _make_move()
    battle = DummyBattle(debug=False)
    random.seed(0)
    apply_damage(attacker, target, move, battle=battle)
    joined = " ".join(battle.logged)
    assert "[DEBUG]" not in joined
