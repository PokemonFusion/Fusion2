import importlib.util
import os
import random
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Minimal pokemon.battle package stub
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
sys.modules["pokemon.battle"] = pkg_battle

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

# Load moves_funcs
moves_path = os.path.join(ROOT, "pokemon", "dex", "functions", "moves_funcs.py")
mv_spec = importlib.util.spec_from_file_location("pokemon.dex.functions.moves_funcs", moves_path)
mv_mod = importlib.util.module_from_spec(mv_spec)
sys.modules[mv_spec.name] = mv_mod
mv_spec.loader.exec_module(mv_mod)
Acrobatics = mv_mod.Acrobatics

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


def run_damage(item=None):
	user = Pokemon("User")
	target = Pokemon("Target")
	base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
	for poke, num in ((user, 1), (target, 2)):
		poke.base_stats = base
		poke.num = num
		poke.types = ["Normal"]
	if item is not None:
		user.item = item
	move = BattleMove(
		"Acrobatics",
		power=55,
		accuracy=100,
		basePowerCallback=Acrobatics().basePowerCallback,
	)
	p1 = BattleParticipant("P1", [user], is_ai=False)
	p2 = BattleParticipant("P2", [target], is_ai=False)
	p1.active = [user]
	p2.active = [target]
	action = Action(p1, ActionType.MOVE, p2, move, move.priority)
	p1.pending_action = action
	battle = Battle(BattleType.WILD, [p1, p2])
	random.seed(0)
	battle.run_turn()
	return target.hp


def test_acrobatics_power_doubles_without_item():
	hp_no_item = run_damage(item=None)
	hp_with_item = run_damage(item="Berry")
	assert hp_no_item < hp_with_item


# Cleanup

del sys.modules["pokemon.dex"]
del sys.modules["pokemon.data"]
