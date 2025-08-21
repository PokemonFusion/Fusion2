import random

import pytest

import pokemon.battle.capture as capture_mod
from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import (
    Action,
    ActionType,
    Battle,
    BattleParticipant,
    BattleType,
)
from pokemon.dex.functions import pokedex_funcs
from pokemon.dex.items.ball_modifiers import BALL_MODIFIERS


@pytest.fixture(autouse=True)
def _stub_catch_rate(monkeypatch):
    """Ensure catch rate lookups return a deterministic value for tests."""
    monkeypatch.setattr(pokedex_funcs, "get_catch_rate", lambda name: 255)


def test_pokeball_capture_marks_opponent_lost():
    attacker = Pokemon("Pikachu")
    defender = Pokemon("Bulbasaur", hp=1, max_hp=100)
    p1 = BattleParticipant("P1", [attacker], is_ai=False)
    p2 = BattleParticipant("P2", [defender], is_ai=False)
    p1.active = [attacker]
    p2.active = [defender]

    action = Action(p1, ActionType.ITEM, p2, item="Pokeball", priority=6)
    p1.pending_action = action

    battle = Battle(BattleType.WILD, [p1, p2])
    random.seed(0)
    battle.run_turn()

    assert p2.has_lost
    assert battle.battle_over


def test_ball_modifier_inventory_and_storage(monkeypatch):
    attacker = Pokemon("Pikachu")
    defender = Pokemon("Bulbasaur", hp=1, max_hp=100)
    p1 = BattleParticipant("P1", [attacker], is_ai=False)
    p2 = BattleParticipant("P2", [defender], is_ai=False)
    p1.active = [attacker]
    p2.active = [defender]

    p1.inventory = {"Ultraball": 1}

    def remove_item(name, quantity=1):
        val = p1.inventory.get(name, 0)
        p1.inventory[name] = val - quantity
        if p1.inventory[name] <= 0:
            p1.inventory.pop(name, None)
        return True

    p1.remove_item = remove_item
    p1.storage = []

    def add_storage(name, level, type_, data=None):
        p1.storage.append(name)

    p1.add_pokemon_to_storage = add_storage

    captured = {}

    def fake_capture(*args, **kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(capture_mod, "attempt_capture", fake_capture)

    action = Action(p1, ActionType.ITEM, p2, item="Ultraball", priority=6)
    p1.pending_action = action

    battle = Battle(BattleType.WILD, [p1, p2])
    battle.run_turn()

    assert captured.get("ball_modifier") == BALL_MODIFIERS["ultraball"]
    assert "Ultraball" not in p1.inventory
    assert "Bulbasaur" in p1.storage


def test_ball_name_with_space(monkeypatch):
    attacker = Pokemon("Pikachu")
    defender = Pokemon("Bulbasaur", hp=1, max_hp=100)
    p1 = BattleParticipant("P1", [attacker], is_ai=False)
    p2 = BattleParticipant("P2", [defender], is_ai=False)
    p1.active = [attacker]
    p2.active = [defender]

    p1.inventory = {"Ultra Ball": 1}

    def remove_item(name, quantity=1):
        val = p1.inventory.get(name, 0)
        p1.inventory[name] = val - quantity
        if p1.inventory[name] <= 0:
            p1.inventory.pop(name, None)
        return True

    p1.remove_item = remove_item
    p1.storage = []

    def add_storage(name, level, type_, data=None):
        p1.storage.append(name)

    p1.add_pokemon_to_storage = add_storage

    captured = {}

    def fake_capture(*args, **kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(capture_mod, "attempt_capture", fake_capture)

    action = Action(p1, ActionType.ITEM, p2, item="Ultra Ball", priority=6)
    p1.pending_action = action

    battle = Battle(BattleType.WILD, [p1, p2])
    battle.run_turn()

    assert captured.get("ball_modifier") == BALL_MODIFIERS["ultraball"]
    assert "Ultra Ball" not in p1.inventory
    assert "Bulbasaur" in p1.storage

