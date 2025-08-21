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

# Load entity dataclasses
ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)
Stats = ent_mod.Stats
Ability = ent_mod.Ability

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
Move = bd_mod.Move

# Load battle engine
eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
eng_mod = importlib.util.module_from_spec(eng_spec)
sys.modules[eng_spec.name] = eng_mod
eng_spec.loader.exec_module(eng_mod)
Battle = eng_mod.Battle
BattleParticipant = eng_mod.BattleParticipant
BattleMove = eng_mod.BattleMove
Action = eng_mod.Action
ActionType = eng_mod.ActionType
BattleType = eng_mod.BattleType


def test_dispatcher_callbacks_fire():
	events = []
	battle_move = BattleMove("Tackle", power=40, accuracy=100)

	user = Pokemon("User")
	user.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
	user.num = 1
	user.types = ["Normal"]
	target = Pokemon("Target")
	target.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
	target.num = 2
	target.types = ["Normal"]

	p1 = BattleParticipant("P1", [user], is_ai=False)
	p2 = BattleParticipant("P2", [target], is_ai=False)
	p1.active = [user]
	p2.active = [target]
	action = Action(p1, ActionType.MOVE, p2, battle_move, battle_move.priority)
	p1.pending_action = action
	battle = Battle(BattleType.WILD, [p1, p2])

	battle.dispatcher.register("switch_in", lambda **_: events.append("switch_in"))
	battle.dispatcher.register("before_move", lambda **_: events.append("before_move"))
	battle.dispatcher.register("after_move", lambda **_: events.append("after_move"))
	battle.dispatcher.register("end_turn", lambda **_: events.append("end_turn"))

	random.seed(0)
	battle.run_turn()

	assert events.count("switch_in") == 2
	assert "before_move" in events
	assert "after_move" in events
	assert "end_turn" in events


# Cleanup
for mod in [
	"pokemon.dex",
	"pokemon.data",
	"pokemon.battle",
	"pokemon.battle.engine",
	"pokemon.battle.damage",
	"pokemon.battle.battledata",
]:
	sys.modules.pop(mod, None)
