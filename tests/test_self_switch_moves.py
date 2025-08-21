import importlib
import os
import sys

import pytest

from tests.test_move_effects import setup_battle
from tests.test_move_effects import setup_env as base_setup_env

"""Tests for moves that cause the user to switch out."""

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


@pytest.fixture
def env():
	"""Provide battle environment including move functions."""
	data = base_setup_env()
	mv_mod = importlib.import_module("pokemon.dex.functions.moves_funcs")
	data["moves_mod"] = mv_mod
	yield data
	for mod in [
		"pokemon.battle",
		"pokemon.battle.utils",
		"pokemon.battle.battledata",
		"pokemon.battle.engine",
		"pokemon.dex",
		"pokemon.dex.entities",
		"pokemon.dex.functions.moves_funcs",
	]:
		sys.modules.pop(mod, None)


def test_parting_shot_switches_user(env):
	"""Using Parting Shot should switch the user out after execution."""
	battle, p1, p2, user, target = setup_battle(env)
	bench = env["Pokemon"]("Bench")
	bench.side = p1.side
	p1.pokemons.append(bench)
	move = env["BattleMove"](
		"Parting Shot",
		power=0,
		accuracy=True,
		onHit=env["moves_mod"].Partingshot().onHit,
		raw={"category": "Status"},
	)
	action = env["Action"](p1, env["ActionType"].MOVE, p2, move, move.priority, pokemon=user)
	p1.pending_action = action
	battle.run_turn()
	assert p1.active[0] is bench
