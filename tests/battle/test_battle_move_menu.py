import sys
import types

# Stub evennia evmenu so importing battle_move works without full evennia setup
sys.modules["evennia.utils.evmenu"] = types.SimpleNamespace(EvMenuGotoAbortMessage=Exception)

from menus import battle_move


def test_route_move_cancel_returns_cancel_node():
	node, kwargs = battle_move._route_move(None, "cancel", slots=[])
	assert node == "cancel_node"
	assert kwargs == {}


def test_route_target_cancel_returns_cancel_node():
	node, kwargs = battle_move._route_target(None, "cancel", move_obj=None)
	assert node == "cancel_node"
	assert kwargs == {}


def test_route_spaced_move_preserves_pp_and_priority(monkeypatch):
	"""The menu resolves a display name to the stored move and its dex data."""
	entry = types.SimpleNamespace(raw={"priority": 1}, name="Quick Attack")
	monkeypatch.setattr(battle_move, "MOVEDEX", {"Quickattack": entry})
	node, kwargs = battle_move._route_move(None, "Quick Attack", slots=["Quickattack"], pp_overrides={0: 3})
	assert node == "choose_target"
	assert kwargs["move_obj"].pp == 3
	assert kwargs["move_obj"].priority == 1
