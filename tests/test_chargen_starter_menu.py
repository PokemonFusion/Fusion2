import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_chargen_with_stubs():
    patched = {
        "pokemon": sys.modules.get("pokemon"),
        "pokemon.data": sys.modules.get("pokemon.data"),
        "pokemon.data.generation": sys.modules.get("pokemon.data.generation"),
        "pokemon.data.starters": sys.modules.get("pokemon.data.starters"),
        "pokemon.data.text": sys.modules.get("pokemon.data.text"),
        "pokemon.dex": sys.modules.get("pokemon.dex"),
        "pokemon.helpers": sys.modules.get("pokemon.helpers"),
        "pokemon.helpers.pokemon_helpers": sys.modules.get("pokemon.helpers.pokemon_helpers"),
        "pokemon.models": sys.modules.get("pokemon.models"),
        "pokemon.models.storage": sys.modules.get("pokemon.models.storage"),
        "utils": sys.modules.get("utils"),
        "utils.enhanced_evmenu": sys.modules.get("utils.enhanced_evmenu"),
        "utils.fusion": sys.modules.get("utils.fusion"),
    }

    try:
        sys.modules["pokemon"] = types.ModuleType("pokemon")
        sys.modules["pokemon"].__path__ = [os.path.join(ROOT, "pokemon")]
        sys.modules["pokemon.data"] = types.ModuleType("pokemon.data")
        sys.modules["pokemon.data"].__path__ = [os.path.join(ROOT, "pokemon", "data")]

        fake_generation = types.ModuleType("pokemon.data.generation")
        fake_generation.NATURES = {}
        fake_generation.generate_pokemon = lambda *args, **kwargs: None
        sys.modules["pokemon.data.generation"] = fake_generation

        fake_starters = types.ModuleType("pokemon.data.starters")
        fake_starters.STARTER_LOOKUP = {"bulbasaur": "bulbasaur"}
        fake_starters.resolve_starter_key = lambda value: fake_starters.STARTER_LOOKUP.get(
            str(value or "").strip().lower()
        )
        fake_starters.is_valid_starter_key = lambda key: key == "bulbasaur"
        fake_starters.get_starter_names = lambda: ["Bulbasaur", "Charmander"]
        sys.modules["pokemon.data.starters"] = fake_starters

        fake_text = types.ModuleType("pokemon.data.text")
        fake_text.ABILITIES_TEXT = {}
        sys.modules["pokemon.data.text"] = fake_text

        fake_dex = types.ModuleType("pokemon.dex")
        fake_dex.POKEDEX = {}
        sys.modules["pokemon.dex"] = fake_dex

        sys.modules["pokemon.helpers"] = types.ModuleType("pokemon.helpers")
        sys.modules["pokemon.helpers"].__path__ = [os.path.join(ROOT, "pokemon", "helpers")]
        fake_helpers = types.ModuleType("pokemon.helpers.pokemon_helpers")
        fake_helpers.create_owned_pokemon = lambda *args, **kwargs: None
        sys.modules["pokemon.helpers.pokemon_helpers"] = fake_helpers

        sys.modules["pokemon.models"] = types.ModuleType("pokemon.models")
        fake_storage = types.ModuleType("pokemon.models.storage")
        fake_storage.ensure_boxes = lambda storage: storage
        sys.modules["pokemon.models.storage"] = fake_storage

        sys.modules["utils"] = types.ModuleType("utils")
        fake_evmenu = types.ModuleType("utils.enhanced_evmenu")
        fake_evmenu.INVALID_INPUT_MSG = "|rInvalid input.|n"
        sys.modules["utils.enhanced_evmenu"] = fake_evmenu
        fake_fusion = types.ModuleType("utils.fusion")
        fake_fusion.record_fusion = lambda *args, **kwargs: None
        sys.modules["utils.fusion"] = fake_fusion

        path = os.path.join(ROOT, "menus", "chargen.py")
        spec = importlib.util.spec_from_file_location("menus.chargen", path)
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


class DummyCaller:
    def __init__(self):
        self.ndb = types.SimpleNamespace(chargen={})
        self.msgs = []

    def msg(self, text):
        self.msgs.append(text)


def test_starter_species_list_aliases_print_valid_options():
    chargen = load_chargen_with_stubs()
    caller = DummyCaller()

    _text, options = chargen.starter_species(caller, "", type="Fire")
    list_option = next(opt for opt in options if "starterlist" in opt["key"])

    for command in ("starterlist", "pokemonlist"):
        caller.msgs.clear()
        node = list_option["goto"](caller, command)

        assert node == ("starter_species", {"type": "Fire"})
        assert len(caller.msgs) == 1
        assert caller.msgs[0].startswith("Starter Pok")
        assert "Bulbasaur, Charmander" in caller.msgs[0]


def test_chargen_selection_callbacks_confirm_choices_once():
    chargen = load_chargen_with_stubs()
    caller = DummyCaller()

    assert chargen._select_chargen_type(caller, "a", chargen_type="human") == ("human_gender", {})
    assert caller.msgs == ["|gSelected character type:|n Human trainer"]

    caller.msgs.clear()
    assert chargen._select_player_gender(caller, "m", gender="Male", next_node="human_type") == (
        "human_type",
        {"gender": "Male"},
    )
    assert caller.msgs == ["|gSelected gender:|n Male"]

    caller.msgs.clear()
    assert chargen._select_favored_type(caller, "fire", type="Fire") == (
        "starter_species",
        {"type": "Fire"},
    )
    assert caller.msgs == ["|gSelected favored type:|n Fire"]

    caller.msgs.clear()
    assert chargen._select_starter_gender(caller, "f", gender="F") == (
        "starter_confirm",
        {"gender": "F"},
    )
    assert caller.msgs == ["|gSelected starter gender:|n Female"]

    caller.msgs.clear()
    assert chargen._select_starter_gender(caller, "f", gender="F") == (
        "starter_confirm",
        {"gender": "F"},
    )
    assert caller.msgs == []


def test_iron_crown_is_rejected_as_chargen_starter():
    chargen = load_chargen_with_stubs()
    caller = DummyCaller()
    caller.ndb.chargen["favored_type"] = "Steel"

    node = chargen._handle_starter_species_input(caller, "Iron Crown")

    assert node == ("starter_species", {"type": "Steel"})
    assert caller.msgs[0] == "|rInvalid input.|n"
    assert "Invalid starter species" in caller.msgs[-1]
