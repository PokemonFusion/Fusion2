"""Tests for the :class:`TurnManager` mixin and turn helpers."""

from tests.test_battle_rebuild import BattleSession, DummyPlayer, DummyRoom


def _setup_battle():
	room = DummyRoom()
	p1 = DummyPlayer(1, room)
	p2 = DummyPlayer(2, room)
	inst = BattleSession(p1, p2)
	inst.start_pvp()
	return inst, p1, p2


def test_prompt_next_turn_uses_helpers(monkeypatch):
	"""`prompt_next_turn` delegates to banner and interface helpers."""

	inst, _, _ = _setup_battle()
	calls = {"banner": False, "render": False}

	monkeypatch.setattr(inst, "_notify_turn_banner", lambda: calls.__setitem__("banner", True))
	monkeypatch.setattr(inst, "_render_interfaces", lambda: calls.__setitem__("render", True))

	inst.prompt_next_turn()

	assert calls["banner"] and calls["render"]


def test_run_turn_persists_state(monkeypatch):
	"""`run_turn` uses state persistence helper when executing turns."""

	inst, p1, p2 = _setup_battle()
	inst.prompt_next_turn = lambda: None  # avoid interface spam
	calls = {"persist": False, "banner": 0}

	monkeypatch.setattr(inst, "_persist_turn_state", lambda: calls.__setitem__("persist", True))

	def fake_banner():
		calls["banner"] += 1

	monkeypatch.setattr(inst, "_notify_turn_banner", fake_banner)

	inst.queue_move("tackle", caller=p1)
	inst.queue_move("tackle", caller=p2)

	assert calls["persist"] is True
	assert calls["banner"] >= 2  # before and after running the turn
