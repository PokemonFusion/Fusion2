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
utils_stub = types.ModuleType("pokemon.battle.utils")
def get_modified_stat(pokemon, stat):
    return getattr(pokemon.base_stats, stat, 0)
utils_stub.get_modified_stat = get_modified_stat
pkg_battle.utils = utils_stub
sys.modules["pokemon.battle"] = pkg_battle
sys.modules["pokemon.battle.utils"] = utils_stub

# Load entity dataclasses
ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)
Stats = ent_mod.Stats

# Minimal pokemon.dex stub
pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.entities = ent_mod
pokemon_dex.MOVEDEX = {}
pokemon_dex.Move = ent_mod.Move
pokemon_dex.Pokemon = ent_mod.Pokemon
sys.modules["pokemon.dex"] = pokemon_dex

# Minimal pokemon.data stub
data_stub = types.ModuleType("pokemon.data")
data_stub.__path__ = []
data_stub.TYPE_CHART = {}
sys.modules["pokemon.data"] = data_stub

# Load damage module
damage_path = os.path.join(ROOT, "pokemon", "battle", "damage.py")
d_spec = importlib.util.spec_from_file_location("pokemon.battle.damage", damage_path)
damage_mod = importlib.util.module_from_spec(d_spec)
sys.modules[d_spec.name] = damage_mod
d_spec.loader.exec_module(damage_mod)
pkg_battle.damage_calc = damage_mod.damage_calc

# Load battledata and engine
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)
Pokemon = bd_mod.Pokemon
Move = bd_mod.Move

eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
engine = importlib.util.module_from_spec(eng_spec)
sys.modules[eng_spec.name] = engine
eng_spec.loader.exec_module(engine)

BattleMove = engine.BattleMove
BattleParticipant = engine.BattleParticipant
Battle = engine.Battle
Action = engine.Action
ActionType = engine.ActionType
BattleType = engine.BattleType


def test_double_turn_order_and_spread_damage():
    base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)

    # Player side
    a1 = Pokemon("A1")
    a2 = Pokemon("A2")
    for idx, poke in enumerate((a1, a2), start=1):
        poke.base_stats = base
        poke.num = idx
        poke.types = ["Normal"]

    # Opponent side
    b1 = Pokemon("B1")
    b2 = Pokemon("B2")
    for idx, poke in enumerate((b1, b2), start=3):
        poke.base_stats = base
        poke.num = idx
        poke.types = ["Normal"]

    spread_move = BattleMove("Surf", power=40, accuracy=100, raw={"target": "allAdjacentFoes"})

    p1 = BattleParticipant("P1", [a1, a2], is_ai=False, max_active=2)
    p2 = BattleParticipant("P2", [b1, b2], is_ai=False, max_active=2)
    p1.active = [a1, a2]
    p2.active = [b1, b2]

    act1 = Action(p1, ActionType.MOVE, p2, spread_move, spread_move.priority, pokemon=a1)
    p1.pending_action = [act1]

    battle = Battle(BattleType.WILD, [p1, p2])
    random.seed(0)
    battle.run_turn()

    damage_first = 100 - b1.hp
    damage_second = 100 - b2.hp
    assert damage_second == int(damage_first * 0.75)

    del sys.modules["pokemon.dex"]
    del sys.modules["pokemon.data"]
