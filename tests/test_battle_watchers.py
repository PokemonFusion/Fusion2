import importlib
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
