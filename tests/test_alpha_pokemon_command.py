import importlib.util
import os
import sys
import types
from contextlib import nullcontext

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_alpha_command():
    patched = {
        "evennia": sys.modules.get("evennia"),
        "pokemon.data.starters": sys.modules.get("pokemon.data.starters"),
        "utils.dex_suggestions": sys.modules.get("utils.dex_suggestions"),
        "utils.locks": sys.modules.get("utils.locks"),
    }
    try:
        fake_evennia = types.ModuleType("evennia")
        fake_evennia.Command = type("Command", (), {})
        sys.modules["evennia"] = fake_evennia

        fake_starters = types.ModuleType("pokemon.data.starters")
        fake_starters.get_starter_names = lambda: ["Bulbasaur", "Charmander"]
        fake_starters.resolve_starter_key = lambda value: {
            "bulbasaur": "bulbasaur",
            "charmander": "charmander",
        }.get(str(value or "").strip().lower())
        sys.modules["pokemon.data.starters"] = fake_starters

        fake_suggestions = types.ModuleType("utils.dex_suggestions")
        fake_suggestions.is_species_not_found_error = lambda err: "not found" in str(err).lower()
        fake_suggestions.species_not_found_message = lambda value: f"Missing species: {value}"
        sys.modules["utils.dex_suggestions"] = fake_suggestions

        fake_locks = types.ModuleType("utils.locks")
        fake_locks.require_no_battle_lock = lambda caller: True
        sys.modules["utils.locks"] = fake_locks

        path = os.path.join(ROOT, "commands", "player", "cmd_alpha.py")
        spec = importlib.util.spec_from_file_location("commands.player.cmd_alpha", path)
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


class DummyLocation:
    def __init__(self, key="Alpha Test Hub", **flags):
        self.key = key
        self.db = types.SimpleNamespace(**flags)


class DummyCaller:
    def __init__(self, location=None):
        self.location = location or DummyLocation()
        self.trainer = types.SimpleNamespace(user=types.SimpleNamespace(key="Tester"))
        self.storage = types.SimpleNamespace()
        self.msgs = []

    def msg(self, text):
        self.msgs.append(text)


def test_alphapokemon_requires_alpha_area():
    mod = load_alpha_command()
    caller = DummyCaller(DummyLocation("Town Square"))

    cmd = mod.CmdAlphaPokemon()
    cmd.caller = caller
    cmd.args = "Bulbasaur"
    cmd.switches = []
    cmd.func()

    assert caller.msgs == ["You can only use this in the alpha testing area."]


def test_alphapokemon_lists_starter_choices():
    mod = load_alpha_command()
    caller = DummyCaller()

    cmd = mod.CmdAlphaPokemon()
    cmd.caller = caller
    cmd.args = ""
    cmd.switches = ["list"]
    cmd.func()

    assert caller.msgs == ["Alpha Pokemon choices:\nBulbasaur, Charmander"]


def test_alphapokemon_validates_against_starter_list():
    mod = load_alpha_command()
    caller = DummyCaller()

    cmd = mod.CmdAlphaPokemon()
    cmd.caller = caller
    cmd.args = "Iron Crown"
    cmd.switches = []
    cmd.func()

    assert "chargen starter list" in caller.msgs[-1]


def test_alphapokemon_places_valid_starter(monkeypatch):
    mod = load_alpha_command()
    caller = DummyCaller(DummyLocation("Testing Lab", alpha_test_area=True))
    pokemon = types.SimpleNamespace(name="Bulbasaur", computed_level=5, party_slot=2)

    cmd = mod.CmdAlphaPokemon()
    cmd.caller = caller
    cmd.args = "Bulbasaur"
    cmd.switches = []
    monkeypatch.setattr(cmd, "_create_and_place", lambda species, trainer, storage: (pokemon, "party", None))
    cmd.func()

    assert caller.msgs == ["Added Bulbasaur (Lv 5) in party slot 2."]


def test_alphapokemon_marks_generated_metadata(monkeypatch):
    mod = load_alpha_command()
    caller = DummyCaller(DummyLocation("Alpha Test Hub", alpha_test_area=True))
    caller.storage = types.SimpleNamespace(get_party=lambda: [])
    created = {}
    placed = []

    fake_db = types.ModuleType("django.db")
    fake_db.transaction = types.SimpleNamespace(atomic=lambda: nullcontext())
    monkeypatch.setitem(sys.modules, "django.db", fake_db)

    fake_timezone = types.ModuleType("django.utils.timezone")
    fake_timezone.now = lambda: "now"
    fake_utils = types.ModuleType("django.utils")
    fake_utils.timezone = fake_timezone
    monkeypatch.setitem(sys.modules, "django.utils", fake_utils)
    monkeypatch.setitem(sys.modules, "django.utils.timezone", fake_timezone)

    fake_generation = types.ModuleType("pokemon.data.generation")
    fake_generation.generate_pokemon = lambda species, level=5: types.SimpleNamespace(
        species=types.SimpleNamespace(name="Bulbasaur"),
        level=level,
        gender="M",
        nature="Hardy",
        ability="Overgrow",
        ivs=types.SimpleNamespace(
            hp=1,
            attack=2,
            defense=3,
            special_attack=4,
            special_defense=5,
            speed=6,
        ),
        moves=["Tackle"],
    )
    monkeypatch.setitem(sys.modules, "pokemon.data.generation", fake_generation)

    fake_helpers = types.ModuleType("pokemon.helpers.pokemon_helpers")

    def fake_create_owned_pokemon(species, trainer, level, **kwargs):
        created.update({"species": species, "trainer": trainer, "level": level, **kwargs})
        return types.SimpleNamespace(name=species, species=species, computed_level=level, party_slot=1)

    fake_helpers.create_owned_pokemon = fake_create_owned_pokemon
    monkeypatch.setitem(sys.modules, "pokemon.helpers.pokemon_helpers", fake_helpers)

    fake_storage = types.ModuleType("pokemon.models.storage")
    fake_storage.assign_to_first_storage_box = lambda storage, pokemon: types.SimpleNamespace(
        name="Box 1"
    )
    fake_storage.move_to_box = lambda pokemon, storage, box: box
    fake_storage.move_to_party = lambda pokemon, storage: placed.append(pokemon)
    monkeypatch.setitem(sys.modules, "pokemon.models.storage", fake_storage)

    cmd = mod.CmdAlphaPokemon()
    cmd.caller = caller
    pokemon, placement, box_name = cmd._create_and_place("bulbasaur", caller.trainer, caller.storage)

    assert pokemon.name == "Bulbasaur"
    assert placement == "party"
    assert box_name is None
    assert placed == [pokemon]
    assert created["met_location"] == "Alpha Test Generator (Alpha Test Hub)"
    assert created["obtained_method"] == "alpha_test"
    assert created["flags"] == ["alpha_test_generated"]
