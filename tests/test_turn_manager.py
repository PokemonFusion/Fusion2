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


def test_run_turn_ends_battle_when_over(monkeypatch):
    """`run_turn` ends the session when the battle engine reports victory."""

    inst, _, _ = _setup_battle()

    for participant in getattr(inst.battle, "participants", []):
        participant.pokemons = [object()]

    def fail_call(*_, **__):  # pragma: no cover - defensive guard
        raise AssertionError("Should not call post-turn helpers when battle is over")

    monkeypatch.setattr(inst, "_persist_turn_state", fail_call)
    monkeypatch.setattr(inst, "prompt_next_turn", fail_call)

    messages: list[str] = []
    monkeypatch.setattr(inst, "msg", lambda text: messages.append(text))

    end_called = {"value": False}
    original_end = inst.end

    def wrapped_end():
        end_called["value"] = True
        original_end()

    monkeypatch.setattr(inst, "end", wrapped_end)

    check_calls = {"count": 0}

    def fake_check_win_conditions():
        check_calls["count"] += 1
        inst.battle.battle_over = True
        return None

    monkeypatch.setattr(inst.battle, "check_win_conditions", fake_check_win_conditions)

    def fake_run_turn():
        inst.battle.battle_over = True

    monkeypatch.setattr(inst.battle, "run_turn", fake_run_turn)

    inst.run_turn()

    assert end_called["value"] is True
    assert any("The battle has ended." in msg for msg in messages)
    assert check_calls["count"] >= 1
