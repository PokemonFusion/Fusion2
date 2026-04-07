import importlib
import json
import types


def test_watchers_receive_messages(monkeypatch):
    monkeypatch.setenv("PF2_NO_EVENNIA", "1")
    from services.battle import instance as instance_module

    importlib.reload(instance_module)

    inst = instance_module.BattleInstance()
    inst.setup(99)
    inst.add_watcher(1)
    inst.add_watcher(2)

    received = {}

    def fake_notify(state, message, room=None):
        for wid in state["watchers"]:
            received.setdefault(wid, []).append(message)

    monkeypatch.setattr(instance_module, "notify_watchers", fake_notify)

    inst.msg("Hello watchers")
    assert received == {1: ["[B#99] Hello watchers"], 2: ["[B#99] Hello watchers"]}

    inst.remove_watcher(1)
    inst.msg("One left")
    assert received == {
        1: ["[B#99] Hello watchers"],
        2: ["[B#99] Hello watchers", "[B#99] One left"],
    }


def test_invalidate_handles_lock_attribute_errors(monkeypatch):
    monkeypatch.setenv("PF2_NO_EVENNIA", "1")
    from services.battle import instance as instance_module

    importlib.reload(instance_module)

    inst = instance_module.BattleInstance()
    inst.setup(13)

    char = types.SimpleNamespace(
        ndb=types.SimpleNamespace(battle_instance=inst),
        db=types.SimpleNamespace(battle_id=13),
    )
    inst.ndb.characters = {1: char}

    def _raise_attr(_char):
        raise AttributeError("missing lock state")

    monkeypatch.setattr(instance_module, "clear_battle_lock", _raise_attr)

    inst.invalidate()

    assert not hasattr(char.ndb, "battle_instance")
    assert not hasattr(char.db, "battle_id")


def test_setup_uses_initial_state_factory(monkeypatch):
    monkeypatch.setenv("PF2_NO_EVENNIA", "1")
    from services.battle import instance as instance_module

    importlib.reload(instance_module)

    seen = {}

    def fake_factory(*, battle_id, initiator_id, now, rng_seed):
        seen["battle_id"] = battle_id
        seen["initiator_id"] = initiator_id
        seen["now"] = now
        seen["rng_seed"] = rng_seed
        return {
            "id": battle_id,
            "rng_seed": rng_seed,
            "started_at": now,
            "last_tick": now,
            "log": [],
            "watchers": [],
            "initiator_id": initiator_id,
            "p1": {
                "trainer_id": initiator_id,
                "party_snapshot": [],
                "active_index": 0,
                "side_effects": [],
            },
            "p2": {
                "trainer_id": None,
                "party_snapshot": [],
                "active_index": 0,
                "side_effects": [],
            },
            "queue": [],
            "turn": 0,
            "phase": "init",
            "weather": None,
            "terrain": None,
            "hazards": {"p1": [], "p2": []},
        }

    monkeypatch.setattr(instance_module, "build_initial_state", fake_factory)
    inst = instance_module.BattleInstance()
    inst.setup(101, initiator_id=7)

    assert seen["battle_id"] == 101
    assert seen["initiator_id"] == 7
    assert isinstance(seen["now"], float)
    assert isinstance(seen["rng_seed"], int)
    assert inst.state["id"] == 101
    assert inst.p1["trainer_id"] == 7
    assert inst.p2["trainer_id"] is None
    assert inst.turn == 0
    assert inst.watchers == []


def test_initial_state_serializes_for_script_db(monkeypatch):
    monkeypatch.setenv("PF2_NO_EVENNIA", "1")
    from services.battle import instance as instance_module

    importlib.reload(instance_module)

    state = instance_module.build_initial_state(
        battle_id=5, initiator_id=22, now=1234.5, rng_seed=99
    )
    encoded = json.dumps(state)
    restored = json.loads(encoded)

    assert restored["id"] == 5
    assert restored["p1"]["trainer_id"] == 22
    assert restored["hazards"] == {"p1": [], "p2": []}
    assert restored["queue"] == []
