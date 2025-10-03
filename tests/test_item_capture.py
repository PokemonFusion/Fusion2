import os
import random
import sys
from types import SimpleNamespace

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

pkg_battle = sys.modules.get("pokemon.battle")
if pkg_battle is not None and getattr(pkg_battle, "__file__", None) is None:
    for name in list(sys.modules):
        if name == "pokemon.battle" or name.startswith("pokemon.battle."):
            sys.modules.pop(name, None)

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
        return capture_mod.CaptureOutcome(caught=True, shakes=3, critical=False)

    monkeypatch.setattr(capture_mod, "attempt_capture", fake_capture)

    action = Action(p1, ActionType.ITEM, p2, item="Ultraball", priority=6)
    p1.pending_action = action

    battle = Battle(BattleType.WILD, [p1, p2])
    battle.run_turn()

    assert captured.get("ball_modifier") == BALL_MODIFIERS["ultraball"]
    assert p1.inventory["Ultraball"] == 1
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
        return capture_mod.CaptureOutcome(caught=True, shakes=2, critical=True)

    monkeypatch.setattr(capture_mod, "attempt_capture", fake_capture)

    action = Action(p1, ActionType.ITEM, p2, item="Ultra Ball", priority=6)
    p1.pending_action = action

    battle = Battle(BattleType.WILD, [p1, p2])
    battle.run_turn()

    assert captured.get("ball_modifier") == BALL_MODIFIERS["ultraball"]
    assert p1.inventory["Ultra Ball"] == 1
    assert "Bulbasaur" in p1.storage


def test_capture_logs_shakes_and_gotcha(monkeypatch):
    attacker = Pokemon("Pikachu")
    defender = Pokemon("Bulbasaur", hp=1, max_hp=100)
    p1 = BattleParticipant("P1", [attacker], is_ai=False)
    p2 = BattleParticipant("P2", [defender], is_ai=False)
    p1.active = [attacker]
    p2.active = [defender]

    p1.inventory = {"Pokeball": 1}
    consumed = {"count": 0}

    def remove_item(name, quantity=1):
        consumed["count"] += 1
        p1.inventory[name] = p1.inventory.get(name, 0) - quantity

    p1.remove_item = remove_item

    def fake_capture(*args, **kwargs):
        return capture_mod.CaptureOutcome(caught=True, shakes=3, critical=False)

    monkeypatch.setattr(capture_mod, "attempt_capture", fake_capture)

    action = Action(p1, ActionType.ITEM, p2, item="Pokeball", priority=6)
    p1.pending_action = action

    battle = Battle(BattleType.WILD, [p1, p2])
    logs: list[str] = []
    battle.log_action = logs.append

    battle.run_turn()

    assert logs.count("The ball shook!") == 3
    assert any("Gotcha!" in line for line in logs)
    assert consumed["count"] == 0


def test_capture_failure_consumes_ball_and_logs(monkeypatch):
    attacker = Pokemon("Pikachu")
    defender = Pokemon("Bulbasaur", hp=5, max_hp=100)
    p1 = BattleParticipant("P1", [attacker], is_ai=False)
    p2 = BattleParticipant("P2", [defender], is_ai=False)
    p1.active = [attacker]
    p2.active = [defender]

    p1.inventory = {"Great Ball": 1}

    def remove_item(name, quantity=1):
        p1.inventory[name] = p1.inventory.get(name, 0) - quantity
        return True

    p1.remove_item = remove_item

    def fake_capture(*args, **kwargs):
        return capture_mod.CaptureOutcome(caught=False, shakes=1, critical=False)

    monkeypatch.setattr(capture_mod, "attempt_capture", fake_capture)

    action = Action(p1, ActionType.ITEM, p2, item="Great Ball", priority=6)
    p1.pending_action = action

    battle = Battle(BattleType.WILD, [p1, p2])
    logs: list[str] = []
    battle.log_action = logs.append

    battle.run_turn()

    assert p1.inventory["Great Ball"] == 0
    assert any("broke free" in line for line in logs)
    assert not p2.has_lost
    assert not battle.battle_over


def test_capture_updates_pokedex_and_transfers_item(monkeypatch):
    attacker = Pokemon("Pikachu")
    defender = Pokemon("Bulbasaur", hp=1, max_hp=100)
    defender.item = "Oran Berry"
    p1 = BattleParticipant("P1", [attacker], is_ai=False)
    p2 = BattleParticipant("P2", [defender], is_ai=False)
    p1.active = [attacker]
    p2.active = [defender]

    class FakeTrainer:
        def __init__(self):
            self.seen = []
            self.caught = []
            self.items = []

        def log_seen_pokemon(self, species):
            self.seen.append(species)

        def log_caught_pokemon(self, species):
            self.caught.append(species)

        def add_item(self, item_name, amount=1):
            self.items.append((item_name, amount))

    class FakePlayer:
        def __init__(self):
            self.ndb = SimpleNamespace(pending_caught_pokemon=[])
            self.seen = []
            self.caught = []

        def mark_seen(self, species):
            self.seen.append(species)

        def mark_caught(self, species):
            self.caught.append(species)

    trainer = FakeTrainer()
    player = FakePlayer()

    p1.trainer = trainer
    p1.player = player

    class Storage:
        def get_party(self):
            return []

    p1.storage = Storage()

    def fake_capture(*args, **kwargs):
        return capture_mod.CaptureOutcome(caught=True, shakes=2, critical=False)

    monkeypatch.setattr(capture_mod, "attempt_capture", fake_capture)

    action = Action(p1, ActionType.ITEM, p2, item="Nest Ball", priority=6)
    p1.pending_action = action

    battle = Battle(BattleType.WILD, [p1, p2])
    logs: list[str] = []
    battle.log_action = logs.append

    battle.run_turn()

    assert trainer.seen == ["Bulbasaur"]
    assert trainer.caught == ["Bulbasaur"]
    assert ("Oran Berry", 1) in trainer.items
    assert player.seen == ["Bulbasaur"]
    assert player.caught == ["Bulbasaur"]
    assert player.ndb.pending_caught_pokemon[-1] == {"species": "Bulbasaur", "to_storage": False}
    assert any("nickname" in line.lower() for line in logs)


def test_full_party_routes_to_storage(monkeypatch):
    attacker = Pokemon("Pikachu")
    defender = Pokemon("Bulbasaur", hp=1, max_hp=100)
    p1 = BattleParticipant("P1", [attacker], is_ai=False)
    p2 = BattleParticipant("P2", [defender], is_ai=False)
    p1.active = [attacker]
    p2.active = [defender]

    trainer = SimpleNamespace(log_seen_pokemon=lambda species: None, log_caught_pokemon=lambda species: None)
    player = SimpleNamespace(ndb=SimpleNamespace(pending_caught_pokemon=[]))
    p1.trainer = trainer
    p1.player = player

    class FullPartyStorage:
        def get_party(self):
            return [object()] * 6

    p1.storage = FullPartyStorage()

    def fake_capture(*args, **kwargs):
        return capture_mod.CaptureOutcome(caught=True, shakes=1, critical=True)

    monkeypatch.setattr(capture_mod, "attempt_capture", fake_capture)

    action = Action(p1, ActionType.ITEM, p2, item="Premier Ball", priority=6)
    p1.pending_action = action

    battle = Battle(BattleType.WILD, [p1, p2])
    logs: list[str] = []
    battle.log_action = logs.append

    battle.run_turn()

    assert player.ndb.pending_caught_pokemon[-1] == {"species": "Bulbasaur", "to_storage": True}
    assert any("storage" in line.lower() for line in logs)
