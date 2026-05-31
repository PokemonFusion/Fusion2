import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_debug_commands():
    patched = {
        "evennia": sys.modules.get("evennia"),
    }
    try:
        fake_evennia = types.ModuleType("evennia")
        fake_evennia.Command = type("Command", (), {})
        sys.modules["evennia"] = fake_evennia

        path = os.path.join(ROOT, "commands", "debug", "command.py")
        spec = importlib.util.spec_from_file_location("commands.debug.command", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        for name, module in patched.items():
            if module is not None:
                sys.modules[name] = module
            else:
                sys.modules.pop(name, None)


class DummyStorage:
    def __init__(self, has_party=False):
        self.has_party = has_party

    def has_party_pokemon(self):
        return self.has_party


class DummyCaller:
    def __init__(self, *, validated=False, has_party=False, chargen=None):
        self.db = types.SimpleNamespace(validated=validated)
        self.ndb = types.SimpleNamespace(chargen=chargen)
        self.storage = DummyStorage(has_party)
        self.msgs = []
        self.choose_calls = []

    def msg(self, text):
        self.msgs.append(text)

    def choose_starter(self, species):
        self.choose_calls.append(species)
        raise AssertionError("direct starter creation should not be called")


def install_fake_menu(menu_calls):
    fake_menu_module = types.ModuleType("menus")
    fake_chargen = types.ModuleType("menus.chargen")
    fake_menu_module.chargen = fake_chargen
    sys.modules["menus"] = fake_menu_module
    sys.modules["menus.chargen"] = fake_chargen

    fake_enhanced = types.ModuleType("utils.enhanced_evmenu")

    def fake_evmenu(*args, **kwargs):
        menu_calls.append((args, kwargs))

    fake_enhanced.EnhancedEvMenu = fake_evmenu
    sys.modules["utils.enhanced_evmenu"] = fake_enhanced


def load_user_with_stubs():
    module_names = [
        "django",
        "django.apps",
        "django.conf",
        "django.core",
        "django.core.exceptions",
        "django.db",
        "django.db.models",
        "django.utils",
        "django.utils.timezone",
        "typeclasses",
        "typeclasses.characters",
        "pokemon.helpers",
        "pokemon.helpers.party_helpers",
        "pokemon.helpers.pokemon_helpers",
        "pokemon.models",
        "pokemon.models.storage",
        "pokemon.utils",
        "pokemon.utils.objresolve",
        "pokemon.user",
        "utils.inventory",
    ]
    patched = {name: sys.modules.get(name) for name in module_names}

    class DummyAtomic:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    try:
        fake_apps = types.ModuleType("django.apps")
        fake_apps.apps = types.SimpleNamespace(get_model=lambda *args, **kwargs: None)
        sys.modules["django"] = types.ModuleType("django")
        sys.modules["django.apps"] = fake_apps

        fake_conf = types.ModuleType("django.conf")
        fake_conf.settings = types.SimpleNamespace()
        sys.modules["django.conf"] = fake_conf

        sys.modules["django.core"] = types.ModuleType("django.core")
        fake_exceptions = types.ModuleType("django.core.exceptions")
        fake_exceptions.ValidationError = type("ValidationError", (Exception,), {})
        sys.modules["django.core.exceptions"] = fake_exceptions

        fake_db = types.ModuleType("django.db")
        fake_db.IntegrityError = type("IntegrityError", (Exception,), {})
        fake_db.transaction = types.SimpleNamespace(atomic=lambda: DummyAtomic())
        sys.modules["django.db"] = fake_db
        fake_models = types.ModuleType("django.db.models")
        fake_models.Max = lambda field: field
        sys.modules["django.db.models"] = fake_models

        sys.modules["django.utils"] = types.ModuleType("django.utils")
        fake_timezone = types.ModuleType("django.utils.timezone")
        fake_timezone.localtime = lambda value: value
        sys.modules["django.utils.timezone"] = fake_timezone

        sys.modules["typeclasses"] = types.ModuleType("typeclasses")
        fake_characters = types.ModuleType("typeclasses.characters")
        fake_characters.Character = type("Character", (), {"at_object_creation": lambda self: None})
        sys.modules["typeclasses.characters"] = fake_characters

        sys.modules["pokemon.helpers"] = types.ModuleType("pokemon.helpers")
        fake_party = types.ModuleType("pokemon.helpers.party_helpers")
        fake_party.get_active_party = lambda caller: []
        fake_party.has_usable_pokemon = lambda caller: False
        sys.modules["pokemon.helpers.party_helpers"] = fake_party
        fake_pokemon_helpers = types.ModuleType("pokemon.helpers.pokemon_helpers")
        fake_pokemon_helpers.create_owned_pokemon = lambda *args, **kwargs: None
        sys.modules["pokemon.helpers.pokemon_helpers"] = fake_pokemon_helpers

        sys.modules["pokemon.models"] = types.ModuleType("pokemon.models")
        fake_storage = types.ModuleType("pokemon.models.storage")
        fake_storage.PokemonPlacement = types.SimpleNamespace(
            LocationType=types.SimpleNamespace(PARTY="party")
        )
        fake_storage.move_to_box = lambda *args, **kwargs: None
        fake_storage.move_to_party = lambda *args, **kwargs: None
        sys.modules["pokemon.models.storage"] = fake_storage

        sys.modules["pokemon.utils"] = types.ModuleType("pokemon.utils")
        fake_objresolve = types.ModuleType("pokemon.utils.objresolve")
        fake_objresolve.resolve_to_obj = lambda value: value
        sys.modules["pokemon.utils.objresolve"] = fake_objresolve

        fake_inventory = types.ModuleType("utils.inventory")
        fake_inventory.Inventory = dict
        fake_inventory.InventoryMixin = type("InventoryMixin", (), {})
        sys.modules["utils.inventory"] = fake_inventory

        path = os.path.join(ROOT, "pokemon", "user.py")
        spec = importlib.util.spec_from_file_location("pokemon.user", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        for name, module in patched.items():
            if module is not None:
                sys.modules[name] = module
            else:
                sys.modules.pop(name, None)


def test_starter_with_species_is_deprecated_and_does_not_create():
    mod = load_debug_commands()
    cmd = mod.CmdChooseStarter()
    caller = DummyCaller(chargen={"type": "human", "player_gender": "Male", "favored_type": "Fire"})
    cmd.caller = caller
    cmd.args = "Bulbasaur"

    cmd.func()

    assert not caller.choose_calls
    assert caller.msgs
    assert "deprecated" in caller.msgs[-1]


def test_starter_with_invalid_species_uses_starter_validation():
    mod = load_debug_commands()
    cmd = mod.CmdChooseStarter()
    caller = DummyCaller(chargen={"type": "human", "player_gender": "Male", "favored_type": "Fire"})
    cmd.caller = caller
    cmd.args = "Iron Crown"

    cmd.func()

    assert not caller.choose_calls
    assert caller.msgs
    assert "not a valid starter species" in caller.msgs[-1]


def test_legacy_choose_starter_method_validates_starter_set():
    mod = load_user_with_stubs()
    caller = DummyCaller(chargen={"type": "human", "player_gender": "Male", "favored_type": "Fire"})

    invalid = mod.User.choose_starter(caller, "Iron Crown")
    valid = mod.User.choose_starter(caller, "Bulbasaur")

    assert "not a valid starter species" in invalid
    assert "Direct starter selection has moved into chargen" in valid


def test_starter_opens_partial_chargen_starter_menu_when_eligible():
    mod = load_debug_commands()
    menu_calls = []
    patched = {
        "menus": sys.modules.get("menus"),
        "menus.chargen": sys.modules.get("menus.chargen"),
        "utils.enhanced_evmenu": sys.modules.get("utils.enhanced_evmenu"),
    }
    try:
        install_fake_menu(menu_calls)
        cmd = mod.CmdChooseStarter()
        caller = DummyCaller(chargen={"type": "human", "player_gender": "Male", "favored_type": "Fire"})
        cmd.caller = caller
        cmd.args = ""

        cmd.func()

        assert menu_calls
        args, kwargs = menu_calls[-1]
        assert args[0] is caller
        assert kwargs["startnode"] == "starter_species"
        assert kwargs["startnode_input"] == ("", {"type": "Fire"})
    finally:
        for name, module in patched.items():
            if module is not None:
                sys.modules[name] = module
            else:
                sys.modules.pop(name, None)


def test_starter_rejected_after_starter_or_chargen_complete():
    mod = load_debug_commands()

    cmd = mod.CmdChooseStarter()
    caller = DummyCaller(has_party=True, chargen={"type": "human", "favored_type": "Fire"})
    cmd.caller = caller
    cmd.args = ""
    cmd.func()
    assert "already have" in caller.msgs[-1]

    cmd = mod.CmdChooseStarter()
    caller = DummyCaller(validated=True, chargen={"type": "human", "favored_type": "Fire"})
    cmd.caller = caller
    cmd.args = ""
    cmd.func()
    assert "already completed chargen" in caller.msgs[-1]
