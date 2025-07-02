import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Minimal pokemon.battle package stub
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
sys.modules["pokemon.battle"] = pkg_battle

# Minimal pokemon.battle.utils stub required by damage module
utils_stub = types.ModuleType("pokemon.battle.utils")
def get_modified_stat(pokemon, stat):
    return getattr(pokemon.base_stats, stat, 0)
utils_stub.get_modified_stat = get_modified_stat
sys.modules["pokemon.battle.utils"] = utils_stub

# Load entity dataclasses for Stats
ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)
Stats = ent_mod.Stats

# Minimal pokemon.dex package stub
pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.entities = ent_mod
pokemon_dex.MOVEDEX = {}
pokemon_dex.Move = ent_mod.Move
pokemon_dex.Pokemon = ent_mod.Pokemon
sys.modules["pokemon.dex"] = pokemon_dex

# Minimal pokemon.data stub used by damage_calc
data_stub = types.ModuleType("pokemon.data")
data_stub.__path__ = []
data_stub.TYPE_CHART = {}
sys.modules["pokemon.data"] = data_stub

# Load damage module and expose damage_calc
damage_path = os.path.join(ROOT, "pokemon", "battle", "damage.py")
d_spec = importlib.util.spec_from_file_location("pokemon.battle.damage", damage_path)
d_mod = importlib.util.module_from_spec(d_spec)
sys.modules[d_spec.name] = d_mod
d_spec.loader.exec_module(d_mod)
pkg_battle.damage_calc = d_mod.damage_calc

# Load battledata for Pokemon container
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)
Pokemon = bd_mod.Pokemon

# Stub moves_funcs with a dummy onSideStart
moves_mod = types.ModuleType("pokemon.dex.functions.moves_funcs")
class Dummy:
    def onSideStart(self, side, source=None):
        side.started = side.started + 1 if hasattr(side, "started") else 1
moves_mod.Dummy = Dummy
sys.modules["pokemon.dex.functions.moves_funcs"] = moves_mod

# Load battle engine
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


def test_on_side_start_triggers_and_stores_condition():
    user = Pokemon("User")
    target = Pokemon("Target")
    base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    for poke in (user, target):
        poke.base_stats = base
        poke.num = 1
        poke.types = ["Normal"]

    move = BattleMove(
        "Dummy",
        power=0,
        accuracy=True,
        raw={
            "sideCondition": "dummycond",
            "target": "allySide",
            "condition": {"onSideStart": "Dummy.onSideStart"},
        },
    )

    p1 = BattleParticipant("P1", [user], is_ai=False)
    p2 = BattleParticipant("P2", [target], is_ai=False)
    p1.active = [user]
    p2.active = [target]
    action = Action(p1, ActionType.MOVE, p2, move, move.priority)
    p1.pending_action = action
    battle = Battle(BattleType.WILD, [p1, p2])
    battle.run_turn()

    assert "dummycond" in p1.side.conditions
    assert getattr(p1.side, "started", 0) == 1

# Cleanup

del sys.modules["pokemon.dex"]
del sys.modules["pokemon.data"]
