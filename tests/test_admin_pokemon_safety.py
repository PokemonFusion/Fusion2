import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class FakeRelation:
    def __init__(self):
        self.clear_count = 0

    def clear(self):
        self.clear_count += 1


class FakePokemon:
    def __init__(self, unique_id="mon-1"):
        self.unique_id = unique_id
        self.name = "Pikachu"
        self.active_users = FakeRelation()
        self.stored_users = FakeRelation()
        self.boxes = FakeRelation()
        self.delete_count = 0
        self.deleted = False

    def delete(self):
        self.delete_count += 1
        self.deleted = True


class FakePokemonManager:
    def __init__(self, pokemon=None):
        self.pokemon = pokemon
        self.lookup = None

    def filter(self, **kwargs):
        self.lookup = kwargs
        return self

    def first(self):
        if not self.pokemon or self.pokemon.deleted:
            return None
        if str(self.pokemon.unique_id) == str(self.lookup.get("unique_id")):
            return self.pokemon
        return None


class FakeCaller:
    def __init__(self):
        self.messages = []

    def msg(self, text):
        self.messages.append(text)


def load_admin_pokemon(monkeypatch, manager):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)

    fake_core = types.ModuleType("pokemon.models.core")
    fake_core.OwnedPokemon = types.SimpleNamespace(objects=manager)
    fake_trainer = types.ModuleType("pokemon.models.trainer")
    fake_trainer.Trainer = object
    monkeypatch.setitem(sys.modules, "pokemon.models.core", fake_core)
    monkeypatch.setitem(sys.modules, "pokemon.models.trainer", fake_trainer)

    path = os.path.join(ROOT, "commands", "admin", "cmd_adminpokemon.py")
    spec = importlib.util.spec_from_file_location("commands.admin.cmd_adminpokemon", path)
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


def run_remove_command(mod, caller, args):
    command = mod.CmdRemovePokemon()
    command.caller = caller
    command.args = args
    command.func()


def test_removepokemon_requires_explicit_confirmation(monkeypatch):
    pokemon = FakePokemon()
    mod = load_admin_pokemon(monkeypatch, FakePokemonManager(pokemon))
    caller = FakeCaller()

    run_remove_command(mod, caller, "mon-1")

    assert not pokemon.deleted
    assert pokemon.delete_count == 0
    assert caller.messages == [
        "This permanently deletes Pokemon mon-1. Repeat with @removepokemon mon-1 confirm to continue."
    ]


def test_removepokemon_confirm_clears_relations_and_deletes_once(monkeypatch):
    pokemon = FakePokemon()
    mod = load_admin_pokemon(monkeypatch, FakePokemonManager(pokemon))
    caller = FakeCaller()

    run_remove_command(mod, caller, "mon-1 confirm")

    assert pokemon.active_users.clear_count == 1
    assert pokemon.stored_users.clear_count == 1
    assert pokemon.boxes.clear_count == 1
    assert pokemon.delete_count == 1
    assert pokemon.deleted
    assert caller.messages == ["Removed Pikachu (mon-1)."]


def test_removepokemon_confirm_is_idempotent_after_delete(monkeypatch):
    pokemon = FakePokemon()
    mod = load_admin_pokemon(monkeypatch, FakePokemonManager(pokemon))
    caller = FakeCaller()

    run_remove_command(mod, caller, "mon-1 confirm")
    run_remove_command(mod, caller, "mon-1 confirm")

    assert pokemon.delete_count == 1
    assert "No Pok" in caller.messages[-1]


def test_removepokemon_confirm_missing_id_does_not_delete(monkeypatch):
    pokemon = FakePokemon()
    mod = load_admin_pokemon(monkeypatch, FakePokemonManager(pokemon))
    caller = FakeCaller()

    run_remove_command(mod, caller, "missing confirm")

    assert not pokemon.deleted
    assert pokemon.delete_count == 0
    assert "No Pok" in caller.messages[-1]
