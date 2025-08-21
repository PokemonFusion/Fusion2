import importlib
import os
import sys

import pytest

from tests.test_move_effects import setup_battle
from tests.test_move_effects import setup_env as base_setup_env

"""Tests for field hazard moves such as Spikes."""

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


@pytest.fixture
def env():
	"""Provide battle environment including hazard handlers."""
	data = base_setup_env()
	mv_mod = importlib.import_module("pokemon.dex.functions.moves_funcs")
	data["moves_mod"] = mv_mod
	data["engine"].moves_funcs = mv_mod
	importlib.import_module("pokemon.battle.conditions").moves_funcs = mv_mod
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


def test_spikes_sets_hazard_and_damages_switch_in(env):
	"""Spikes should record a hazard layer and damage entering Pokémon."""
	battle, p1, p2, user, target = setup_battle(env)
	move = env["BattleMove"](
		"Spikes",
		power=0,
		accuracy=True,
		raw={
			"category": "Status",
			"sideCondition": "spikes",
			"target": "foeSide",
			"condition": {"onSideStart": "Spikes.onSideStart", "onEntryHazard": "Spikes.onEntryHazard"},
		},
	)
	action = env["Action"](p1, env["ActionType"].MOVE, p2, move, move.priority)
	p1.pending_action = action
	battle.run_turn()
	assert p2.side.hazards.get("spikes") == 1
	entrant = env["Pokemon"]("SwitchIn")
	entrant.side = p2.side
	battle.apply_entry_hazards(entrant)
	assert entrant.hp == 88
