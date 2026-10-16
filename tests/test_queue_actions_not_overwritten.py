from uuid import uuid4

import pytest

from tests.test_battle_rebuild import BattleSession, DummyPlayer, DummyRoom
from tests.test_battle_restore_missing_state import DummyPlayer as PartyPlayer
from tests.test_battle_restore_missing_state import DummyPokemonModel


def _setup_battle():
	"""Create a simple two-player battle for testing."""
	room = DummyRoom()
	p1 = DummyPlayer(1, room)
	p2 = DummyPlayer(2, room)
	# Queue tests use owned-party selectors, so both model and battle copies
	# need the stable identities supplied by production storage.
	for player in (p1, p2):
		for pokemon in player.storage.party:
			pokemon.unique_id = str(uuid4())
	inst = BattleSession(p1, p2)
	inst.start_pvp()
	return inst, p1, p2


def test_queue_move_does_not_overwrite_existing_action():
	inst, p1, _ = _setup_battle()
	inst.queue_move("tackle", caller=p1)
	inst.queue_move("growl", caller=p1)
	assert inst.state.declare["A1"]["move"].lower() == "tackle"


def test_queue_switch_does_not_overwrite_existing_action():
	inst, p1, _ = _setup_battle()
	inst.queue_switch(2, caller=p1)
	inst.queue_switch(3, caller=p1)
	assert inst.state.declare["A1"]["switch"] == 2


def test_queue_item_does_not_overwrite_existing_action():
	inst, p1, _ = _setup_battle()
	inst.queue_item("potion", caller=p1)
	inst.queue_item("superpotion", caller=p1)
	assert inst.state.declare["A1"]["item"].lower() == "potion"


@pytest.mark.parametrize("item_name", ["Potion", "Antidote"])
@pytest.mark.parametrize("team", ["A", "B"])
def test_item_queue_and_restore_keep_correct_side(item_name, team):
	"""Queued items retain safe targets through an actual session restore."""
	room = DummyRoom()
	p1 = PartyPlayer(1, room, [DummyPokemonModel("Squirtle")])
	p2 = PartyPlayer(2, room, [DummyPokemonModel("Rattata")])
	inst = BattleSession(p1, p2)
	inst.start_pvp()
	caller = p1 if team == "A" else p2
	actor = inst.battle.participants[0 if team == "A" else 1]
	actor.inventory = {item_name: 1}
	inst.queue_item(item_name, caller=caller)
	expected = team
	assert inst.state.declare[f"{team}1"]["target"] == f"{expected}1"
	# Restore must rebuild the engine action, not merely the UI declaration.
	room = caller.location
	room.ndb.battle_instances = {}
	restored = BattleSession.restore(room, inst.battle_id)
	actor = restored.battle.participants[0 if team == "A" else 1]
	target = restored.battle.participants[0 if expected == "A" else 1]
	assert actor.pending_action.item == item_name
	assert actor.pending_action.target is target


def test_queue_run_does_not_overwrite_existing_action():
	inst, p1, _ = _setup_battle()
	inst.queue_run(caller=p1)
	inst.queue_run(caller=p1)
	assert inst.state.declare["A1"]["run"] == "1"


def test_cannot_declare_new_action_if_already_declared():
	inst, p1, _ = _setup_battle()
	inst.queue_move("tackle", caller=p1)
	before = inst.state.declare["A1"].copy()
	inst.queue_switch(2, caller=p1)
	assert inst.state.declare["A1"] == before


def test_turn_runs_and_clears_declarations():
	"""Battle runs once all actions are declared and clears declarations."""
	inst, p1, p2 = _setup_battle()
	inst.prompt_next_turn = lambda: None
	ran = {"flag": False}

	def fake_run_turn():
		ran["flag"] = True

	inst.battle.run_turn = fake_run_turn

	inst.queue_move("tackle", caller=p1)
	inst.queue_move("tackle", caller=p2)

	assert ran["flag"] is True
	assert inst.state.declare == {}
