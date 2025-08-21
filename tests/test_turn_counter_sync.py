"""Ensure battle state turn counter matches engine turn count."""

from tests.test_battle_rebuild import BattleSession, DummyPlayer, DummyRoom


def test_state_turn_matches_engine_after_running_turn() -> None:
	"""Running a turn should update ``state.turn`` for the battle UI."""

	room = DummyRoom()
	p1 = DummyPlayer(1, room)
	p2 = DummyPlayer(2, room)
	inst = BattleSession(p1, p2)
	inst.start_pvp()

	assert inst.state.turn == 1
	assert inst.battle.turn_count == 1

	inst.queue_move("tackle", caller=p1)
	inst.queue_move("tackle", caller=p2)

	assert inst.battle.turn_count == 2
	assert inst.state.turn == 2
