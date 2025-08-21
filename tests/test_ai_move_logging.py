import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_engine():
	path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
	spec = importlib.util.spec_from_file_location("pokemon.battle.engine", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)
	return mod


def test_ai_move_choice_logged():
	# stub dex before loading engine
	orig_pdex = sys.modules.get("pokemon.dex")
	orig_entities = sys.modules.get("pokemon.dex.entities")
	pdex = types.ModuleType("pokemon.dex")
	pdex.__path__ = []
	pdex.MOVEDEX = {}
	sys.modules["pokemon.dex"] = pdex

	ent_mod = types.ModuleType("pokemon.dex.entities")

	class Move:
		def __init__(self, name, priority=0):
			self.name = name
			self.priority = priority

	ent_mod.Move = Move
	sys.modules["pokemon.dex.entities"] = ent_mod

	orig_engine = sys.modules.get("pokemon.battle.engine")
	eng = load_engine()

	logs = []

	class DummyLogger:
		def info(self, msg, *args):
			logs.append(msg % args)

	eng.battle_logger = DummyLogger()

	poke = types.SimpleNamespace(moves=[types.SimpleNamespace(name="Tackle")])
	ai = eng.BattleParticipant("AI", [poke], is_ai=True)
	player = eng.BattleParticipant("Player", [poke], is_ai=False)
	ai.active = [poke]
	player.active = [poke]
	battle = eng.Battle(eng.BattleType.WILD, [ai, player])

	action = ai.choose_action(battle)

	assert action.move.name == "Tackle"
	assert logs and "AI chooses Tackle" in logs[0]

	if orig_pdex is not None:
		sys.modules["pokemon.dex"] = orig_pdex
	else:
		sys.modules.pop("pokemon.dex", None)
	if orig_entities is not None:
		sys.modules["pokemon.dex.entities"] = orig_entities
	else:
		sys.modules.pop("pokemon.dex.entities", None)
	if orig_engine is not None:
		sys.modules["pokemon.battle.engine"] = orig_engine
	else:
		sys.modules.pop("pokemon.battle.engine", None)
