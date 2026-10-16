"""Regression tests for PP spending across stored and display move names."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from .helpers import build_battle, load_modules


@pytest.mark.parametrize(
    ("stored_name", "display_name"),
    [
        ("Watergun", "Water Gun"),
        ("Dragonrage", "Dragon Rage"),
        ("Quickattack", "Quick Attack"),
        ("willowisp", "Will-O-Wisp"),
    ],
)
def test_spending_pp_updates_stored_slot_and_battle_snapshot(stored_name, display_name):
    """Display spelling must select the saved move and update cached PP too."""
    battle, attacker, _ = build_battle()
    move = load_modules()["BattleMove"](display_name, pp=5)
    cached_move = SimpleNamespace(name=stored_name, pp=5)
    slot = SimpleNamespace(
        move=SimpleNamespace(name=stored_name), current_pp=5, save=Mock(),
    )
    other = SimpleNamespace(
        move=SimpleNamespace(name="Tackle"), current_pp=35, save=Mock(),
    )
    attacker.activemoveslot_set = SimpleNamespace(all=lambda: [other, slot])
    attacker.moves = [cached_move]

    battle.deduct_pp(attacker, move)

    assert slot.current_pp == move.pp == cached_move.pp == 4
    slot.save.assert_called_once_with(update_fields=["current_pp"])
    assert other.current_pp == 35
    other.save.assert_not_called()
    assert attacker.to_dict()["moves"][0]["pp"] == 4


def test_spending_pp_without_stored_slots_uses_normalized_move_name():
    """Temporary battle moves must also retain spending between actions."""
    battle, attacker, _ = build_battle()
    move = load_modules()["BattleMove"]("Water Gun", pp=5)
    cached_move = SimpleNamespace(name="Watergun", pp=5)
    attacker.moves = [cached_move]

    battle.deduct_pp(attacker, move)

    assert move.pp == cached_move.pp == 4


def test_stored_pp_uses_event_cost_and_stops_at_zero(monkeypatch):
    """Modified PP costs cannot make stored PP negative or leave stale PP."""
    battle, attacker, _ = build_battle()
    move = load_modules()["BattleMove"]("Water Gun", pp=5)
    cached_move = SimpleNamespace(name="Watergun", pp=5)
    slot = SimpleNamespace(
        move=SimpleNamespace(name="Watergun"), current_pp=1, save=Mock(),
    )
    attacker.activemoveslot_set = [slot]
    attacker.moves = [cached_move]
    monkeypatch.setattr(battle, "runEvent", lambda *args: 2)

    battle.deduct_pp(attacker, move)
    battle.deduct_pp(attacker, move)

    assert slot.current_pp == move.pp == cached_move.pp == 0
    slot.save.assert_called_once_with(update_fields=["current_pp"])
