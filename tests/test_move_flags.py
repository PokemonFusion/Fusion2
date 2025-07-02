import os
import sys
import types
import importlib.util
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
sys.modules["pokemon.battle"] = pkg_battle

ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)
Stats = ent_mod.Stats

pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.entities = ent_mod
pokemon_dex.MOVEDEX = {}
pokemon_dex.Move = ent_mod.Move
pokemon_dex.Pokemon = ent_mod.Pokemon
sys.modules["pokemon.dex"] = pokemon_dex

data_stub = types.ModuleType("pokemon.data")
data_stub.__path__ = []
data_stub.TYPE_CHART = {}
sys.modules["pokemon.data"] = data_stub

# damage module
damage_path = os.path.join(ROOT, "pokemon", "battle", "damage.py")
d_spec = importlib.util.spec_from_file_location("pokemon.battle.damage", damage_path)
damage_mod = importlib.util.module_from_spec(d_spec)
sys.modules[d_spec.name] = damage_mod
d_spec.loader.exec_module(damage_mod)
pkg_battle.damage_calc = damage_mod.damage_calc

# battledata
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)
Pokemon = bd_mod.Pokemon

# battle engine
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

def test_move_sets_tempvals():
    user = Pokemon("User")
    target = Pokemon("Target")
    base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    for poke, num in ((user, 1), (target, 2)):
        poke.base_stats = base
        poke.num = num
        poke.types = ["Normal"]

    move = BattleMove("Tackle", power=40, accuracy=100)
    p1 = BattleParticipant("P1", [user], is_ai=False)
    p2 = BattleParticipant("P2", [target], is_ai=False)
    p1.active = [user]
    p2.active = [target]
    action = Action(p1, ActionType.MOVE, p2, move, move.priority)
    p1.pending_action = action

    battle = Battle(BattleType.WILD, [p1, p2])
    random.seed(0)

    battle.start_turn()
    battle.run_switch()
    battle.run_after_switch()
    battle.run_move()

    assert user.tempvals.get("moved") is True
    assert target.tempvals.get("took_damage") is True

    battle.run_faint()
    battle.residual()
    battle.end_turn()

# cleanup

del sys.modules["pokemon.dex"]
del sys.modules["pokemon.data"]
