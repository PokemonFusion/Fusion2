import importlib
import os
import sys
from unittest.mock import patch

import pytest

from tests.test_move_effects import setup_battle
from tests.test_move_effects import setup_env as base_setup_env

"""Tests covering multi-hit move behaviour."""

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


@pytest.fixture
def env():
	"""Provide environment including damage module."""
	data = base_setup_env()
	dex_mod = sys.modules["pokemon.dex"]
	ent_mod = sys.modules["pokemon.dex.entities"]
	dex_mod.Move = ent_mod.Move
	dex_mod.Pokemon = ent_mod.Pokemon
	dmg_path = os.path.join(ROOT, "pokemon", "battle", "damage.py")
	spec = importlib.util.spec_from_file_location("pokemon.battle.damage", dmg_path)
	dmg_mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = dmg_mod
	spec.loader.exec_module(dmg_mod)
	data["damage"] = dmg_mod
	yield data
	for mod in [
		"pokemon.battle",
		"pokemon.battle.utils",
		"pokemon.battle.battledata",
		"pokemon.battle.engine",
		"pokemon.battle.damage",
		"pokemon.dex",
		"pokemon.dex.entities",
	]:
		sys.modules.pop(mod, None)


def test_triple_kick_hits_three_times(env, monkeypatch):
	"""A multihit move should invoke damage calculation the expected number of times."""
	battle, p1, p2, user, target = setup_battle(env)
	Stats = sys.modules["pokemon.dex.entities"].Stats
	base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
	user.base_stats = base
	target.base_stats = base
	dmg_mod = env["damage"]
	orig_calc = dmg_mod.damage_calc
	hits = {}

	def wrapped_calc(att, tar, move, battle=None, *, spread=False):
		result = orig_calc(att, tar, move, battle=battle, spread=spread)
		hits["count"] = len(result.debug.get("damage", []))
		return result

	# Ensure random elements resolve deterministically during the test
	with (
		patch("pokemon.battle.engine.random.random", return_value=0.0),
		patch("pokemon.battle.damage.random.randint", return_value=100),
	):
		monkeypatch.setattr(dmg_mod, "damage_calc", wrapped_calc)
		move = env["BattleMove"]("Triple Kick", power=10, accuracy=True, raw={"multihit": 3})
		action = env["Action"](p1, env["ActionType"].MOVE, p2, move, move.priority)
		p1.pending_action = action
		battle.run_turn()
	assert hits.get("count") == 3
