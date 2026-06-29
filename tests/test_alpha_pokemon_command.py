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
        fake_suggestions.normalize_dex_key = (
            lambda value: str(value or "").replace(" ", "").replace("-", "").replace("'", "").lower()
        )
        fake_suggestions.species_not_found_message = lambda value: f"Missing species: {value}"
        fake_suggestions.suggest_name = lambda query, candidates, **kwargs: next(
            (candidate for candidate in candidates if str(candidate).lower().startswith(str(query or "").lower()[:3])),
            None,
        )
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
    def __init__(self, key="Alpha Test Hub", contents=None, **flags):
        self.key = key
        self.contents = list(contents or [])
        self.db = types.SimpleNamespace(**flags)


class DummyCaller:
    def __init__(self, location=None):
        self.location = location or DummyLocation()
        self.trainer = types.SimpleNamespace(user=types.SimpleNamespace(key="Tester"))
        self.storage = types.SimpleNamespace()
        self.msgs = []

    def msg(self, text):
        self.msgs.append(text)

    def get_active_pokemon_by_slot(self, slot):
        return getattr(self, "pokemon", None) if slot == 1 else None


class DummyLearnedMoves(list):
    def filter(self, **kwargs):
        name = str(kwargs.get("name__iexact", "")).lower()
        return DummyLearnedMoves([move for move in self if move.name.lower() == name])

    def exists(self):
        return bool(self)


class DummyPokemon:
    def __init__(self, species="Pikachu", name="Pika", learned=None):
        self.species = species
        self.name = name
        self.learned_moves = DummyLearnedMoves(
            [types.SimpleNamespace(name=move) for move in learned or []]
        )
        self.flags = []
        self.saved = False
        self.save_update_fields = None

    def save(self, update_fields=None):
        self.saved = True
        self.save_update_fields = update_fields


def alpha_terminal():
    return types.SimpleNamespace(
        key="Alpha Move Terminal",
        db=types.SimpleNamespace(alpha_move_terminal=True),
    )


def patch_move_learning_modules(monkeypatch, taught):
    fake_middleware = types.ModuleType("pokemon.middleware")
    fake_middleware.get_moveset_by_name = lambda species: (
        species,
        {
            "level-up": [(1, "tackle")],
            "machine": ["thunderbolt", "swift"],
            "tutor": ["irontail"],
            "egg": ["fakeeggmove"],
        },
    )
    fake_middleware.get_move_by_name = lambda move: (
        move,
        {
            "thunderbolt": {"name": "Thunderbolt"},
            "swift": {"name": "Swift"},
            "irontail": {"name": "Iron Tail"},
        }.get(move, {"name": str(move).title()}),
    )
    monkeypatch.setitem(sys.modules, "pokemon.middleware", fake_middleware)

    fake_move_learning = types.ModuleType("pokemon.utils.move_learning")

    def fake_learn_move(pokemon, move_name, caller=None, prompt=False, on_exit=None):
        taught.append((pokemon, move_name, prompt))
        if caller:
            caller.msg(f"{pokemon.name} learned {move_name}.")

    fake_move_learning.learn_move = fake_learn_move
    monkeypatch.setitem(sys.modules, "pokemon.utils.move_learning", fake_move_learning)


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


def test_alphapokemon_parses_list_slash_args():
    mod = load_alpha_command()
    caller = DummyCaller()

    cmd = mod.CmdAlphaPokemon()
    cmd.caller = caller
    cmd.args = "/list"
    cmd.switches = []
    cmd.parse()
    cmd.func()

    assert cmd.args == ""
    assert cmd.switches == ["list"]
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


def test_alphalearn_requires_alpha_area():
    mod = load_alpha_command()
    caller = DummyCaller(DummyLocation("Town Square", contents=[alpha_terminal()]))
    caller.pokemon = DummyPokemon()

    cmd = mod.CmdAlphaLearnMove()
    cmd.caller = caller
    cmd.args = "1=Thunderbolt"
    cmd.switches = []
    cmd.func()

    assert caller.msgs == ["You can only use this in the alpha testing area."]


def test_alphalearn_requires_terminal():
    mod = load_alpha_command()
    caller = DummyCaller(DummyLocation("Alpha Test Hub", alpha_test_area=True))
    caller.pokemon = DummyPokemon()

    cmd = mod.CmdAlphaLearnMove()
    cmd.caller = caller
    cmd.args = "1=Thunderbolt"
    cmd.switches = []
    cmd.func()

    assert caller.msgs == ["You need to use this near an Alpha Move Terminal."]


def test_alphalearn_lists_machine_and_tutor_moves(monkeypatch):
    mod = load_alpha_command()
    taught = []
    patch_move_learning_modules(monkeypatch, taught)
    caller = DummyCaller(DummyLocation("Alpha Test Hub", contents=[alpha_terminal()]))
    caller.pokemon = DummyPokemon()

    cmd = mod.CmdAlphaLearnMove()
    cmd.caller = caller
    cmd.args = "1"
    cmd.switches = ["list"]
    cmd.func()

    assert caller.msgs == ["Alpha terminal moves for Pika:\nIron Tail, Swift, Thunderbolt"]
    assert taught == []


def test_alphalearn_parses_list_slash_args(monkeypatch):
    mod = load_alpha_command()
    taught = []
    patch_move_learning_modules(monkeypatch, taught)
    caller = DummyCaller(DummyLocation("Alpha Test Hub", contents=[alpha_terminal()]))
    caller.pokemon = DummyPokemon()

    cmd = mod.CmdAlphaLearnMove()
    cmd.caller = caller
    cmd.args = "/list 1"
    cmd.switches = []
    cmd.parse()
    cmd.func()

    assert cmd.args == "1"
    assert cmd.switches == ["list"]
    assert caller.msgs == ["Alpha terminal moves for Pika:\nIron Tail, Swift, Thunderbolt"]
    assert taught == []


def test_alphalearn_rejects_non_machine_or_tutor_move(monkeypatch):
    mod = load_alpha_command()
    taught = []
    patch_move_learning_modules(monkeypatch, taught)
    caller = DummyCaller(DummyLocation("Alpha Test Hub", contents=[alpha_terminal()]))
    caller.pokemon = DummyPokemon()

    cmd = mod.CmdAlphaLearnMove()
    cmd.caller = caller
    cmd.args = "1=Tackle"
    cmd.switches = []
    cmd.func()

    assert caller.msgs == ["Pika cannot learn Tackle through the alpha move terminal."]
    assert taught == []


def test_alphalearn_teaches_machine_move_and_marks_flag(monkeypatch):
    mod = load_alpha_command()
    taught = []
    patch_move_learning_modules(monkeypatch, taught)
    caller = DummyCaller(DummyLocation("Alpha Test Hub", contents=[alpha_terminal()]))
    caller.pokemon = DummyPokemon()

    cmd = mod.CmdAlphaLearnMove()
    cmd.caller = caller
    cmd.args = "1=Thunderbolt"
    cmd.switches = []
    cmd.func()

    assert taught == [(caller.pokemon, "Thunderbolt", True)]
    assert caller.msgs == ["Pika learned Thunderbolt."]
    assert caller.pokemon.flags == ["alpha_teach:thunderbolt"]
    assert caller.pokemon.save_update_fields == ["flags"]


def test_alphalearn_rejects_already_known_move(monkeypatch):
    mod = load_alpha_command()
    taught = []
    patch_move_learning_modules(monkeypatch, taught)
    caller = DummyCaller(DummyLocation("Alpha Test Hub", contents=[alpha_terminal()]))
    caller.pokemon = DummyPokemon(learned=["Thunderbolt"])

    cmd = mod.CmdAlphaLearnMove()
    cmd.caller = caller
    cmd.args = "1=Thunderbolt"
    cmd.switches = []
    cmd.func()

    assert caller.msgs == ["Pika already knows Thunderbolt."]
    assert taught == []
