import importlib.util
import os
import random
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Setup minimal pokemon.battle package with utils
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
utils_stub = types.ModuleType("pokemon.battle.utils")
utils_stub.get_modified_stat = lambda p, s: getattr(p.base_stats, s, 0)
utils_stub.apply_boost = lambda *a, **k: None
pkg_battle.utils = utils_stub
sys.modules["pokemon.battle"] = pkg_battle
sys.modules["pokemon.battle.utils"] = utils_stub

# Load entity classes
ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)
Stats = ent_mod.Stats
Ability = ent_mod.Ability
Item = ent_mod.Item

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


def test_before_turn_callbacks_and_sleep():
	calls = []

	def abil_cb(poke, battle):
		calls.append("ability")

	def item_cb(pokemon=None, battle=None):
		calls.append("item")

	ability = Ability(name="A", num=0, raw={"onBeforeTurn": abil_cb})
	item = Item(name="I", num=0, raw={"onBeforeTurn": item_cb})

	user = Pokemon("User")
	user.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
	user.ability = ability
	user.item = item
	user.status = "slp"
	user.tempvals = {"slp_turns": 2}
	user.moves = [BattleMove("Tackle", power=40, accuracy=100)]

	opponent = Pokemon("Opp")
	opponent.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
	opponent.moves = [BattleMove("Tackle", power=40, accuracy=100)]

	p1 = BattleParticipant("P1", [user], is_ai=False)
	p2 = BattleParticipant("P2", [opponent], is_ai=False)
	p1.active = [user]
	p2.active = [opponent]
	action = Action(p1, ActionType.MOVE, p2, user.moves[0], user.moves[0].priority)
	p1.pending_action = action
	battle = Battle(BattleType.WILD, [p1, p2])
	random.seed(0)

	battle.start_turn()
	battle.before_turn()
	assert set(calls) == {"ability", "item"}
	assert user.tempvals.get("slp_turns") == 1


def test_flinch_prevents_move_once():
	user = Pokemon("User")
	user.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
	user.moves = [BattleMove("Tackle", power=40, accuracy=100)]
	user.volatiles = {"flinch": {}}

	target = Pokemon("Target")
	target.base_stats = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
	target.moves = [BattleMove("Tackle", power=40, accuracy=100)]

	p1 = BattleParticipant("P1", [user], is_ai=False)
	p2 = BattleParticipant("P2", [target], is_ai=False)
	p1.active = [user]
	p2.active = [target]
	action = Action(p1, ActionType.MOVE, p2, user.moves[0], user.moves[0].priority)
	p1.pending_action = action
	battle = Battle(BattleType.WILD, [p1, p2])
	random.seed(0)

	battle.start_turn()
	battle.before_turn()
	battle.run_move()
	assert "flinch" not in getattr(user, "volatiles", {})
	assert target.hp == 100


# Cleanup modules
for mod in [
	"pokemon.dex",
	"pokemon.data",
	"pokemon.battle.utils",
	"pokemon.battle",
	"pokemon.battle.engine",
	"pokemon.battle.damage",
]:
	sys.modules.pop(mod, None)
