import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_cmd_party(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)

    fake_locks = types.ModuleType("utils.locks")
    fake_locks.require_no_battle_lock = lambda caller: True
    monkeypatch.setitem(sys.modules, "utils.locks", fake_locks)

    path = os.path.join(ROOT, "commands", "player", "cmd_party.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_party", path)
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


def install_transaction(monkeypatch, snapshotters=()):
    class FakeAtomic:
        def __enter__(self):
            self._restore = [snapshotter() for snapshotter in snapshotters]
            return self

        def __exit__(self, exc_type, exc, tb):
            if exc_type:
                for restore in reversed(self._restore):
                    restore()
            return False

    fake_django = types.ModuleType("django")
    fake_db = types.ModuleType("django.db")
    fake_db.transaction = types.SimpleNamespace(atomic=lambda: FakeAtomic())
    fake_django.db = fake_db
    monkeypatch.setitem(sys.modules, "django", fake_django)
    monkeypatch.setitem(sys.modules, "django.db", fake_db)


class FakePokemon:
    def __init__(self, *, held_item="", fail_save=False):
        self.name = "Pikachu"
        self.held_item = held_item
        self.fail_save = fail_save
        self.save_calls = 0

    def save(self):
        self.save_calls += 1
        if self.fail_save:
            raise RuntimeError("pokemon save failed")


class FakeItem:
    def __init__(self, *, delete_result=True):
        self.key = "Oran Berry"
        self.delete_result = delete_result
        self.delete_calls = 0

    def delete(self):
        self.delete_calls += 1
        return self.delete_result


class FakeCaller:
    def __init__(self, pokemon, item):
        self.pokemon = pokemon
        self.item = item
        self.messages = []

    def msg(self, text):
        self.messages.append(text)

    def get_active_pokemon_by_slot(self, slot):
        return self.pokemon if slot == 1 else None

    def search(self, item_name, location=None):
        return self.item if item_name == self.item.key else None


def test_hold_success_sets_held_item_and_deletes_carried_item(monkeypatch):
    mod = load_cmd_party(monkeypatch)
    pokemon = FakePokemon()
    item = FakeItem(delete_result=True)
    caller = FakeCaller(pokemon, item)
    install_transaction(monkeypatch)

    command = mod.CmdSetHoldItem()
    command.caller = caller
    command.args = "1=Oran Berry"
    command.func()

    assert pokemon.held_item == "Oran Berry"
    assert pokemon.save_calls == 1
    assert item.delete_calls == 1
    assert caller.messages == ["Pikachu is now holding Oran Berry."]


def test_hold_save_failure_keeps_carried_item_and_restores_held_item(monkeypatch):
    mod = load_cmd_party(monkeypatch)
    pokemon = FakePokemon(fail_save=True)
    item = FakeItem(delete_result=True)
    caller = FakeCaller(pokemon, item)
    install_transaction(monkeypatch)

    command = mod.CmdSetHoldItem()
    command.caller = caller
    command.args = "1=Oran Berry"
    command.func()

    assert pokemon.held_item == ""
    assert item.delete_calls == 0
    assert caller.messages == ["Unable to set held item; your carried item was not removed."]


def test_hold_delete_failure_does_not_leave_pokemon_holding_item(monkeypatch):
    mod = load_cmd_party(monkeypatch)
    pokemon = FakePokemon()
    item = FakeItem(delete_result=False)
    caller = FakeCaller(pokemon, item)
    install_transaction(monkeypatch)

    command = mod.CmdSetHoldItem()
    command.caller = caller
    command.args = "1=Oran Berry"
    command.func()

    assert pokemon.held_item == ""
    assert item.delete_calls == 1
    assert caller.messages == ["Unable to set held item; your carried item was not removed."]


def test_hold_refuses_to_overwrite_existing_held_item(monkeypatch):
    mod = load_cmd_party(monkeypatch)
    pokemon = FakePokemon(held_item="Sitrus Berry")
    item = FakeItem(delete_result=True)
    caller = FakeCaller(pokemon, item)
    install_transaction(monkeypatch)

    command = mod.CmdSetHoldItem()
    command.caller = caller
    command.args = "1=Oran Berry"
    command.func()

    assert pokemon.held_item == "Sitrus Berry"
    assert pokemon.save_calls == 0
    assert item.delete_calls == 0
    assert caller.messages == ["Pikachu is already holding Sitrus Berry."]
