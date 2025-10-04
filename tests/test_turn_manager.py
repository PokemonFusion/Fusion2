"""Tests for the :class:`TurnManager` mixin and turn helpers."""

import types

from tests.test_battle_rebuild import BattleSession, DummyPlayer, DummyRoom, bi_mod


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
    calls = {"headline": False, "render": False}

    def record_headline(*_, **__):
        calls["headline"] = True

    def record_render(*_, **__):
        calls["render"] = True

    monkeypatch.setattr(inst, "_announce_turn_headline", record_headline)
    monkeypatch.setattr(inst, "_render_interfaces", record_render)

    inst.prompt_next_turn()

    assert calls["headline"] and calls["render"]


def test_prompt_next_turn_calls_prompt_hook(monkeypatch):
    """`prompt_next_turn` invokes the active Pokémon prompt hook when available."""

    inst, _, _ = _setup_battle()
    called = {"count": 0}

    def record_prompt():
        called["count"] += 1

    monkeypatch.setattr(inst, "_prompt_active_pokemon", record_prompt)

    inst.prompt_next_turn()

    assert called["count"] == 1


def test_prompt_active_pokemon_announces_names(monkeypatch):
    """`_prompt_active_pokemon` tells trainers which Pokémon to command."""

    inst, p1, p2 = _setup_battle()
    deliveries: list[tuple] = []

    def record_msg(target, text):
        deliveries.append((target, text))

    monkeypatch.setattr(inst, "_msg_to", record_msg)

    pokemon_a = types.SimpleNamespace(name="Alpha")
    pokemon_b = types.SimpleNamespace(name="Beta")
    inst.data.turndata.positions = {
        "A1": types.SimpleNamespace(pokemon=pokemon_a),
        "B1": types.SimpleNamespace(pokemon=pokemon_b),
    }

    inst._prompt_active_pokemon()

    assert any(target is p1 and "Choose an action for" in text for target, text in deliveries)
    assert any(target is p2 and "Choose an action for" in text for target, text in deliveries)


def test_run_turn_persists_state(monkeypatch):
    """`run_turn` uses state persistence helper when executing turns."""

    inst, p1, p2 = _setup_battle()
    inst.prompt_next_turn = lambda: None  # avoid interface spam
    calls = {"persist": False, "banner": []}

    monkeypatch.setattr(inst, "_persist_turn_state", lambda: calls.__setitem__("persist", True))

    def fake_banner(*_, **__):
        calls["banner"].append(__.get("upcoming", False))

    monkeypatch.setattr(inst, "_notify_turn_banner", fake_banner)

    inst.queue_move("tackle", caller=p1)
    inst.queue_move("tackle", caller=p2)

    assert calls["persist"] is True
    assert calls["banner"] == [True, False]


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


def test_waiting_message_follows_interface(monkeypatch):
    """`maybe_run_turn` shows the field UI before the waiting notice."""

    inst, _, _ = _setup_battle()

    monkeypatch.setattr(inst, "is_turn_ready", lambda: False)

    waiting_pokemon = types.SimpleNamespace(name="Bulbasaur")

    class _DummyPosition:
        pokemon = waiting_pokemon

        @staticmethod
        def getAction():
            return None

    inst.logic.data = types.SimpleNamespace(
        turndata=types.SimpleNamespace(positions={"slot": _DummyPosition()})
    )

    events: list[tuple] = []

    def record_broadcast(session, *, waiting_on=None):
        events.append(("broadcast", session, waiting_on))

    def record_send(session, target, *, waiting_on=None):
        events.append(("send", target, waiting_on))

    monkeypatch.setattr(bi_mod, "broadcast_interfaces", record_broadcast)
    monkeypatch.setattr(bi_mod, "send_interface_to", record_send)
    monkeypatch.setattr(inst, "msg", lambda text: events.append(("msg", text)))

    inst.maybe_run_turn()

    assert events[0][0] == "broadcast"
    assert events[-1] == ("msg", "Waiting on Bulbasaur...")
    assert all(kind != "send" for kind, *_ in events)
    assert events[0][2] == "Bulbasaur"


def test_duplicate_queue_skips_waiting_broadcast(monkeypatch):
    """Duplicate declarations avoid spamming waiting notices to others."""

    inst, p1, _ = _setup_battle()

    monkeypatch.setattr(inst, "is_turn_ready", lambda: False)

    waiting_pokemon = types.SimpleNamespace(name="Squirtle")

    class _DummyPosition:
        pokemon = waiting_pokemon

        @staticmethod
        def getAction():
            return None

    inst.logic.data = types.SimpleNamespace(
        turndata=types.SimpleNamespace(positions={"slot": _DummyPosition()})
    )

    events: list[tuple] = []

    def record_broadcast(session, *, waiting_on=None):  # pragma: no cover - guard
        events.append(("broadcast", session, waiting_on))

    def record_send(session, target, *, waiting_on=None):
        events.append(("send", target, waiting_on))

    monkeypatch.setattr(bi_mod, "broadcast_interfaces", record_broadcast)
    monkeypatch.setattr(bi_mod, "send_interface_to", record_send)
    monkeypatch.setattr(inst, "msg", lambda text: events.append(("msg", text)))
    monkeypatch.setattr(inst, "_msg_to", lambda target, text: events.append(("to", target, text)))

    inst.maybe_run_turn(actor=p1, notify_waiting=False)

    assert all(kind != "msg" for kind, *_ in events)
    assert all(kind != "to" for kind, *_ in events)
    assert events == [("send", p1, "Squirtle")]


def test_maybe_run_turn_auto_queues_ai(monkeypatch):
    """AI opponents should select actions without waiting prompts."""

    inst, p1, _ = _setup_battle()

    positions = inst.data.turndata.positions
    pos_a = positions.get("A1")
    pos_b = positions.get("B1")
    assert pos_a and pos_b

    pokemon_a = types.SimpleNamespace(name="Alpha")
    pokemon_b = types.SimpleNamespace(name="Beta")
    pos_a.pokemon = pokemon_a
    pos_b.pokemon = pokemon_b
    inst.battle.participants[0].active = [pokemon_a]
    inst.battle.participants[1].active = [pokemon_b]

    pos_a.declareAttack("B1", "tackle")
    inst.state.declare["A1"] = {"move": "tackle", "target": "B1"}
    pos_b.removeDeclare()

    def fake_ready():
        return bool(pos_a.getAction() and pos_b.getAction())

    monkeypatch.setattr(inst, "is_turn_ready", fake_ready)

    messages: list[str] = []
    monkeypatch.setattr(inst, "msg", lambda text: messages.append(text))

    monkeypatch.setattr(inst, "run_turn", lambda: None)

    auto_calls = {"result": None}

    def fake_auto():
        pos_b.declareAttack("A1", "tackle")
        inst.state.declare["B1"] = {"move": "tackle", "target": "A1"}
        auto_calls["result"] = True
        return True

    monkeypatch.setattr(inst, "_auto_queue_ai_actions", fake_auto)

    inst.maybe_run_turn(actor=p1)

    assert messages == []
    assert auto_calls["result"] is True
    assert pos_b.getAction() == "tackle"
    assert inst.state.declare.get("B1", {}).get("move") == "tackle"
