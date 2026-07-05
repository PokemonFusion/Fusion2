import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_cmd_account(monkeypatch):
    fake_django = types.ModuleType("django")
    fake_django_conf = types.ModuleType("django.conf")
    fake_django_conf.settings = types.SimpleNamespace(MAX_NR_CHARACTERS=4)
    fake_django.conf = fake_django_conf
    monkeypatch.setitem(sys.modules, "django", fake_django)
    monkeypatch.setitem(sys.modules, "django.conf", fake_django_conf)

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    fake_evennia.search_account = lambda *args, **kwargs: []
    fake_evennia.search_object = lambda *args, **kwargs: []
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)

    fake_account_models = types.ModuleType("evennia.accounts.models")
    fake_account_models.AccountDB = types.SimpleNamespace(objects=types.SimpleNamespace(all=lambda: []))
    monkeypatch.setitem(sys.modules, "evennia.accounts", types.ModuleType("evennia.accounts"))
    monkeypatch.setitem(sys.modules, "evennia.accounts.models", fake_account_models)

    fake_default_account = types.ModuleType("evennia.commands.default.account")
    fake_default_account.CmdCharCreate = fake_evennia.Command
    monkeypatch.setitem(sys.modules, "evennia.commands", types.ModuleType("evennia.commands"))
    monkeypatch.setitem(sys.modules, "evennia.commands.default", types.ModuleType("evennia.commands.default"))
    monkeypatch.setitem(sys.modules, "evennia.commands.default.account", fake_default_account)

    fake_storage = types.ModuleType("pokemon.models.storage")
    fake_storage.move_to_box = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "pokemon.models.storage", fake_storage)

    path = os.path.join(ROOT, "commands", "player", "cmd_account.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_account", path)
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


class FakePokemon:
    def __init__(self, unique_id="mon-1", species="Pikachu", *, trainer=None):
        self.unique_id = unique_id
        self.species = species
        self.nickname = ""
        self.trainer = trainer
        self.save_updates = []

    def save(self, update_fields=None):
        self.save_updates.append(update_fields)


class FakeStorage:
    def __init__(self, party=(), *, stored=(), fail_add=False):
        self.party = list(party)
        self.stored = list(stored)
        self.fail_add = fail_add

    def get_party(self):
        return list(self.party)

    def get_stored_pokemon(self):
        return list(self.stored)

    def remove_active_pokemon(self, pokemon):
        self.party.remove(pokemon)

    def add_active_pokemon(self, pokemon):
        if self.fail_add:
            raise RuntimeError("target party full")
        if pokemon not in self.party:
            self.party.append(pokemon)


class FakeCharacter:
    def __init__(self, key, *, account=None, storage=None, pokemon=None, target=None, trainer=None):
        self.key = key
        self.account = account or object()
        self.storage = storage or FakeStorage()
        self._pokemon = pokemon
        self._target = target
        self.trainer = trainer or types.SimpleNamespace(name=f"{key} trainer")
        self.messages = []

    def msg(self, text):
        self.messages.append(text)

    def search(self, query):
        return self._target

    def get_pokemon_by_id(self, ident):
        if self._pokemon and self._pokemon.unique_id == ident:
            return self._pokemon
        return None


def test_trade_restores_party_pokemon_when_target_add_fails(monkeypatch):
    cmd_account = load_cmd_account(monkeypatch)
    pokemon = FakePokemon()
    target = FakeCharacter("Misty", storage=FakeStorage(fail_add=True))
    caller = FakeCharacter(
        "Ash",
        storage=FakeStorage([pokemon]),
        pokemon=pokemon,
        target=target,
    )
    monkeypatch.setattr(cmd_account, "require_no_battle_lock", lambda caller: True)
    command = cmd_account.CmdTradePokemon()
    command.caller = caller
    command.args = "mon-1=Misty"

    command.func()

    assert caller.storage.get_party() == [pokemon]
    assert target.storage.get_party() == []
    assert pokemon.trainer is None
    assert caller.messages == ["Trade failed; Pikachu was returned to your party. target party full"]
    assert target.messages == []


def test_trade_success_moves_party_pokemon_and_transfers_trainer(monkeypatch):
    cmd_account = load_cmd_account(monkeypatch)
    source_trainer = types.SimpleNamespace(name="Ash trainer")
    target_trainer = types.SimpleNamespace(name="Misty trainer")
    pokemon = FakePokemon(trainer=source_trainer)
    target = FakeCharacter("Misty", storage=FakeStorage(), trainer=target_trainer)
    caller = FakeCharacter(
        "Ash",
        storage=FakeStorage([pokemon]),
        pokemon=pokemon,
        target=target,
        trainer=source_trainer,
    )
    monkeypatch.setattr(cmd_account, "require_no_battle_lock", lambda caller: True)
    command = cmd_account.CmdTradePokemon()
    command.caller = caller
    command.args = "mon-1=Misty"

    command.func()

    assert caller.storage.get_party() == []
    assert target.storage.get_party() == [pokemon]
    assert pokemon.trainer is target_trainer
    assert pokemon.save_updates == [["trainer"]]
    assert caller.messages == ["You traded Pikachu to Misty."]
    assert target.messages == ["Ash traded Pikachu to you."]


def test_boxed_trade_is_explicitly_unsupported_and_does_not_move_pokemon(monkeypatch):
    cmd_account = load_cmd_account(monkeypatch)
    pokemon = FakePokemon()
    target = FakeCharacter("Misty", storage=FakeStorage())
    caller = FakeCharacter(
        "Ash",
        storage=FakeStorage(stored=[pokemon]),
        pokemon=pokemon,
        target=target,
    )
    move_calls = []
    monkeypatch.setattr(cmd_account, "move_to_box", lambda *args, **kwargs: move_calls.append((args, kwargs)))
    monkeypatch.setattr(cmd_account, "require_no_battle_lock", lambda caller: True)
    command = cmd_account.CmdTradePokemon()
    command.caller = caller
    command.args = "mon-1=Misty"

    command.func()

    assert caller.storage.get_stored_pokemon() == [pokemon]
    assert target.storage.get_party() == []
    assert move_calls == []
    assert caller.messages == ["Boxed Pokemon trades are not supported yet. Withdraw the Pokemon to your party first."]
    assert target.messages == []
