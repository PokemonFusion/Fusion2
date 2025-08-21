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
