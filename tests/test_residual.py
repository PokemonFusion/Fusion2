import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Create minimal pokemon.battle package to avoid heavy dependencies
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
sys.modules["pokemon.battle"] = pkg_battle

# Load battledata
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
battledata = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = battledata
bd_spec.loader.exec_module(battledata)
Pokemon = battledata.Pokemon

# Load engine
engine_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", engine_path)
eng_mod = importlib.util.module_from_spec(eng_spec)
sys.modules[eng_spec.name] = eng_mod
eng_spec.loader.exec_module(eng_mod)
Battle = eng_mod.Battle
BattleParticipant = eng_mod.BattleParticipant
BattleType = eng_mod.BattleType


def setup_battle(status):
	p1 = Pokemon("Burner", level=1, hp=80, max_hp=80)
	setattr(p1, "status", status)
	if status == "tox":
		setattr(p1, "toxic_counter", 1)
	p2 = Pokemon("Target", level=1, hp=100, max_hp=100)
	part1 = BattleParticipant("P1", [p1])
	part2 = BattleParticipant("P2", [p2])
	part1.active = [p1]
	part2.active = [p2]
	return Battle(BattleType.WILD, [part1, part2]), p1, p2


def test_burn_residual_damage():
	battle, p1, _ = setup_battle("brn")
	battle.residual()
	assert p1.hp == 70


def test_poison_residual_damage():
	battle, p1, _ = setup_battle("psn")
	battle.residual()
	assert p1.hp == 70


def test_toxic_residual_increases_each_turn():
	battle, p1, _ = setup_battle("tox")
	battle.residual()
	assert p1.hp == 75
	battle.residual()
	assert p1.hp == 65


def test_toxic_converts_on_switch_out():
	p1 = Pokemon("Burner", level=1, hp=80, max_hp=80)
	p1.status = "tox"
	p1.toxic_counter = 1
	bench = Pokemon("Bench", level=1, hp=80, max_hp=80)
	part1 = BattleParticipant("P1", [p1, bench])
	part2 = BattleParticipant("P2", [Pokemon("Target", level=1, hp=80, max_hp=80)])
	part1.active = [p1]
	part2.active = [part2.pokemons[0]]
	battle = Battle(BattleType.WILD, [part1, part2])
	part1.active = [bench]
	battle.run_after_switch()
	assert p1.status == "psn"
	assert p1.toxic_counter == 0
