import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module(accounts=None, characters=None):
    originals = {
        name: sys.modules.get(name)
        for name in (
            "django",
            "django.conf",
            "evennia",
            "evennia.accounts",
            "evennia.accounts.models",
            "evennia.commands",
            "evennia.commands.default",
            "evennia.commands.default.account",
            "pokemon",
            "pokemon.models",
            "pokemon.models.storage",
        )
    }

    fake_django = types.ModuleType("django")
    fake_django_conf = types.ModuleType("django.conf")
    fake_django_conf.settings = types.SimpleNamespace(MAX_NR_CHARACTERS=4)
    fake_django.conf = fake_django_conf
    sys.modules["django"] = fake_django
    sys.modules["django.conf"] = fake_django_conf

    class FakeCommand:
        def msg(self, message):
            self.caller.msg(message)

    def search_account(query, exact=True):
        lowered = (query or "").strip().lower()
        return [account for account in accounts or [] if account.key.lower() == lowered]

    def search_object(query, *args, **kwargs):
        lowered = (query or "").strip().lower()
        return [character for character in characters or [] if character.key.lower() == lowered]

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = FakeCommand
    fake_evennia.search_account = search_account
    fake_evennia.search_object = search_object
    sys.modules["evennia"] = fake_evennia

    class FakeObjects:
        @staticmethod
        def all():
            return list(accounts or [])

    class FakeAccountDB:
        objects = FakeObjects()

    fake_account_models = types.ModuleType("evennia.accounts.models")
    fake_account_models.AccountDB = FakeAccountDB
    fake_accounts = types.ModuleType("evennia.accounts")
    fake_accounts.models = fake_account_models
    sys.modules["evennia.accounts"] = fake_accounts
    sys.modules["evennia.accounts.models"] = fake_account_models

    fake_default_account = types.ModuleType("evennia.commands.default.account")
    fake_default_account.CmdCharCreate = FakeCommand
    fake_default = types.ModuleType("evennia.commands.default")
    fake_default.account = fake_default_account
    fake_commands = types.ModuleType("evennia.commands")
    fake_commands.default = fake_default
    sys.modules["evennia.commands"] = fake_commands
    sys.modules["evennia.commands.default"] = fake_default
    sys.modules["evennia.commands.default.account"] = fake_default_account

    fake_storage = types.ModuleType("pokemon.models.storage")
    fake_storage.move_to_box = lambda *args, **kwargs: None
    fake_models = types.ModuleType("pokemon.models")
    fake_models.storage = fake_storage
    fake_pokemon = types.ModuleType("pokemon")
    fake_pokemon.models = fake_models
    sys.modules["pokemon"] = fake_pokemon
    sys.modules["pokemon.models"] = fake_models
    sys.modules["pokemon.models.storage"] = fake_storage

    path = os.path.join(ROOT, "commands", "player", "cmd_account.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_account", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    def restore():
        sys.modules.pop("commands.player.cmd_account", None)
        for name, original in originals.items():
            if original is not None:
                sys.modules[name] = original
            else:
                sys.modules.pop(name, None)

    return mod, restore


class FakeAccount:
    def __init__(self, key, ident, characters=None):
        self.key = key
        self.name = key
        self.id = ident
        self.characters = list(characters or [])
        self.messages = []

    def msg(self, message):
        self.messages.append(message)


class FakeCharacter:
    def __init__(self, key, ident):
        self.key = key
        self.name = key
        self.id = ident
        self.dbref = f"#{ident}"

    def is_typeclass(self, path, exact=False):
        return path == "typeclasses.characters.Character"


def call_alts(mod, caller, args="", switches=None):
    cmd = mod.CmdAlts()
    cmd.caller = caller
    cmd.args = args
    cmd.switches = switches or []
    cmd.func()
    return caller.messages[-1]


def test_alts_lists_characters_for_account():
    misty = FakeCharacter("Misty", 101)
    brock = FakeCharacter("Brock", 102)
    account = FakeAccount("Trainer", 1, [misty, brock])
    mod, restore = load_cmd_module(accounts=[account], characters=[misty, brock])

    try:
        output = call_alts(mod, account, args="Trainer")
    finally:
        restore()

    assert output == "Characters for Trainer: Misty (#101), Brock (#102)"


def test_alts_char_finds_account_for_character():
    misty = FakeCharacter("Misty", 101)
    brock = FakeCharacter("Brock", 102)
    account = FakeAccount("Trainer", 1, [misty, brock])
    staff = FakeAccount("Staff", 2)
    mod, restore = load_cmd_module(accounts=[account, staff], characters=[misty, brock])

    try:
        output = call_alts(mod, staff, args="Misty", switches=["char"])
    finally:
        restore()

    assert "Misty (#101) is on account Trainer." in output
    assert "Characters on that account: Misty (#101), Brock (#102)" in output


def test_alts_falls_back_to_character_lookup():
    misty = FakeCharacter("Misty", 101)
    account = FakeAccount("Trainer", 1, [misty])
    staff = FakeAccount("Staff", 2)
    mod, restore = load_cmd_module(accounts=[account, staff], characters=[misty])

    try:
        output = call_alts(mod, staff, args="Misty")
    finally:
        restore()

    assert output.startswith("Misty (#101) is on account Trainer.")


def test_alts_uses_staff_lock():
    mod, restore = load_cmd_module()
    try:
        assert "perm(Helper)" in mod.CmdAlts.locks
        assert "perm(Wizards)" in mod.CmdAlts.locks
    finally:
        restore()
