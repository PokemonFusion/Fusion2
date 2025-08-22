import importlib.util
import os
import sys
import types

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def setup_env():
	for mod in [
		"pokemon.battle",
		"pokemon.battle.utils",
		"pokemon.battle.battledata",
		"pokemon.battle.engine",
		"pokemon.dex",
		"pokemon.dex.entities",
	]:
		sys.modules.pop(mod, None)

	# Load battle utils for apply_boost
	utils_path = os.path.join(ROOT, "pokemon", "battle", "utils.py")
	utils_spec = importlib.util.spec_from_file_location("pokemon.battle.utils", utils_path)
	utils_mod = importlib.util.module_from_spec(utils_spec)
	sys.modules[utils_spec.name] = utils_mod
	utils_spec.loader.exec_module(utils_mod)

	# Minimal pokemon.battle package
	pkg_battle = types.ModuleType("pokemon.battle")
	pkg_battle.__path__ = []
	pkg_battle.utils = utils_mod
	sys.modules["pokemon.battle"] = pkg_battle

	# Load entities for Move dataclass
	ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
	ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
	ent_mod = importlib.util.module_from_spec(ent_spec)
	sys.modules[ent_spec.name] = ent_mod
	ent_spec.loader.exec_module(ent_mod)

	# Minimal pokemon.dex package
	pokemon_dex = types.ModuleType("pokemon.dex")
	pokemon_dex.__path__ = []
	pokemon_dex.entities = ent_mod
	pokemon_dex.MOVEDEX = {}
	sys.modules["pokemon.dex"] = pokemon_dex

	# Load battledata and engine
	bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
	bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
	bd_mod = importlib.util.module_from_spec(bd_spec)
	sys.modules[bd_spec.name] = bd_mod
	bd_spec.loader.exec_module(bd_mod)

	eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
	eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
	eng_mod = importlib.util.module_from_spec(eng_spec)
	sys.modules[eng_spec.name] = eng_mod
	eng_spec.loader.exec_module(eng_mod)

	return {
		"Pokemon": bd_mod.Pokemon,
		"BattleMove": eng_mod.BattleMove,
		"BattleParticipant": eng_mod.BattleParticipant,
		"Battle": eng_mod.Battle,
		"Action": eng_mod.Action,
		"ActionType": eng_mod.ActionType,
		"BattleType": eng_mod.BattleType,
		"engine": eng_mod,
	}


@pytest.fixture
def env():
	data = setup_env()
	yield data
	for mod in [
		"pokemon.battle",
		"pokemon.battle.utils",
		"pokemon.battle.battledata",
		"pokemon.battle.engine",
		"pokemon.dex",
		"pokemon.dex.entities",
	]:
		sys.modules.pop(mod, None)


def setup_battle(env):
	Pokemon = env["Pokemon"]
	BattleParticipant = env["BattleParticipant"]
	Battle = env["Battle"]
	BattleType = env["BattleType"]

	user = Pokemon("User")
	target = Pokemon("Target")
	part1 = BattleParticipant("P1", [user], is_ai=False)
	part2 = BattleParticipant("P2", [target], is_ai=False)
	part1.active = [user]
	part2.active = [target]
	battle = Battle(BattleType.WILD, [part1, part2])
	return battle, part1, part2, user, target


def test_growl_lowers_attack(env, monkeypatch):
	battle, p1, p2, user, target = setup_battle(env)
	engine = env["engine"]
	monkeypatch.setattr(engine, "_apply_move_damage", lambda *a, **k: None)
	move = env["BattleMove"](
		"Growl",
		power=0,
		accuracy=True,
		raw={"boosts": {"atk": -1}},
	)
	action = env["Action"](p1, env["ActionType"].MOVE, p2, move, move.priority)
	p1.pending_action = action
	battle.run_turn()
	assert target.boosts["attack"] == -1
