import importlib.util
import os
import random
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Minimal pokemon.battle package
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
sys.modules["pokemon.battle"] = pkg_battle

# Load battledata module
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)
Pokemon = bd_mod.Pokemon

# Load engine
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


def test_residual_event_before_end_turn():
	events = []
	burned = Pokemon("Burned", level=1, hp=80, max_hp=80)
	burned.status = "brn"
	target = Pokemon("Target", level=1, hp=100, max_hp=100)
	p1 = BattleParticipant("P1", [burned])
	p2 = BattleParticipant("P2", [target])
	p1.active = [burned]
	p2.active = [target]
	battle = Battle(BattleType.WILD, [p1, p2])
	battle.dispatcher.register("residual", lambda **_: events.append("residual"))
	battle.dispatcher.register("end_turn", lambda **_: events.append("end_turn"))
	random.seed(0)
	battle.run_turn()
	assert events.index("residual") < events.index("end_turn")
	assert burned.hp < 80
