"""Tests for the high level AI moveset generation."""

import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Ensure any earlier test stubs don't interfere with imports
for mod in ["pokemon", "pokemon.battle", "pokemon.battle.ai"]:
    sys.modules.pop(mod, None)

from pokemon.battle.ai import generate_moveset


class DummyMove:
    def __init__(self, name, mtype, category, source, tags=None, priority=0):
        self.name = name
        self.type = mtype
        self.category = category
        self.source = source
        self.tags = tags or []
        self.priority = priority


class DummyPokemon:
    def __init__(self):
        self.types = ["Ground"]
        self.stats = types.SimpleNamespace(
            attack=120, special_attack=60, speed=95, hp=90, special_defense=70
        )
        self.move_pool = [
            DummyMove("Earthquake", "Ground", "Physical", "tm_all"),
            DummyMove("Rock Slide", "Rock", "Physical", "level_up", ["coverage"]),
            DummyMove(
                "Swords Dance", "Normal", "Status", "level_up", ["setup", "status"]
            ),
            DummyMove(
                "Stealth Rock", "Rock", "Status", "tm_all", ["hazard", "status"]
            ),
            DummyMove("Recover", "Normal", "Status", "egg", ["heal", "status"]),
        ]


def test_generate_moveset_high_level():
    poke = DummyPokemon()
    moves = generate_moveset(poke, 3, "tactician")
    assert len(moves) == 4
    assert any(m.type == "Ground" for m in moves)
    assert any(
        set(getattr(m, "tags", [])) & {"status", "utility", "setup", "hazard"}
        or getattr(m, "category", "").lower() == "status"
        for m in moves
    )


def test_generate_moveset_source_filter():
    poke = DummyPokemon()
    moves = generate_moveset(poke, 0, "balanced")
    assert moves and all(m.source == "level_up" for m in moves)
