import os
import sys
import types
import importlib.util
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Minimal pokemon.battle package stub
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
sys.modules["pokemon.battle"] = pkg_battle

# Load capture module and attach to package
cap_path = os.path.join(ROOT, "pokemon", "battle", "capture.py")
cap_spec = importlib.util.spec_from_file_location("pokemon.battle.capture", cap_path)
cap_mod = importlib.util.module_from_spec(cap_spec)
sys.modules["pokemon.battle.capture"] = cap_mod
cap_spec.loader.exec_module(cap_mod)
pkg_battle.capture = cap_mod

# Load battledata for Pokemon container
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)
Pokemon = bd_mod.Pokemon

# Stub catch rate function
pokedex_funcs = types.ModuleType("pokemon.dex.functions.pokedex_funcs")
pokedex_funcs.get_catch_rate = lambda name: 255
sys.modules["pokemon.dex.functions.pokedex_funcs"] = pokedex_funcs

# Load battle engine
eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
engine = importlib.util.module_from_spec(eng_spec)
sys.modules[eng_spec.name] = engine
eng_spec.loader.exec_module(engine)

BattleParticipant = engine.BattleParticipant
Battle = engine.Battle
Action = engine.Action
ActionType = engine.ActionType
BattleType = engine.BattleType


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


def test_ball_modifier_inventory_and_storage():
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

    cap_mod.attempt_capture = fake_capture

    from pokemon.dex.items.ball_modifiers import BALL_MODIFIERS

    action = Action(p1, ActionType.ITEM, p2, item="Ultraball", priority=6)
    p1.pending_action = action

    battle = Battle(BattleType.WILD, [p1, p2])
    battle.run_turn()

    assert captured.get("ball_modifier") == BALL_MODIFIERS["ultraball"]
    assert "Ultraball" not in p1.inventory
    assert "Bulbasaur" in p1.storage

