import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_chargen_module():
    path = os.path.join(ROOT, "menus", "chargen.py")
    spec = importlib.util.spec_from_file_location("menus.chargen", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_finish_fusion_stores_level_and_exp():
    patched = {
        "pokemon": sys.modules.get("pokemon"),
        "pokemon.data": sys.modules.get("pokemon.data"),
        "pokemon.data.generation": sys.modules.get("pokemon.data.generation"),
        "pokemon.data.starters": sys.modules.get("pokemon.data.starters"),
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
        sys.modules["pokemon.data"] = types.ModuleType("pokemon.data")
        fake_generation = types.ModuleType("pokemon.data.generation")
        fake_generation.NATURES = {}
        fake_generation.generate_pokemon = lambda *args, **kwargs: None
        sys.modules["pokemon.data.generation"] = fake_generation
        fake_starters = types.ModuleType("pokemon.data.starters")
        fake_starters.STARTER_LOOKUP = {}
        fake_starters.get_starter_names = lambda: []
        sys.modules["pokemon.data.starters"] = fake_starters
        fake_dex = types.ModuleType("pokemon.dex")
        fake_dex.POKEDEX = {}
        sys.modules["pokemon.dex"] = fake_dex
        sys.modules["pokemon.helpers"] = types.ModuleType("pokemon.helpers")
        fake_helpers = types.ModuleType("pokemon.helpers.pokemon_helpers")
        fake_helpers.create_owned_pokemon = lambda *args, **kwargs: None
        sys.modules["pokemon.helpers.pokemon_helpers"] = fake_helpers
        sys.modules["pokemon.models"] = types.ModuleType("pokemon.models")
        fake_storage = types.ModuleType("pokemon.models.storage")
        fake_storage.ensure_boxes = lambda storage: storage
        sys.modules["pokemon.models.storage"] = fake_storage
        sys.modules["utils"] = types.ModuleType("utils")
        fake_evmenu = types.ModuleType("utils.enhanced_evmenu")
        fake_evmenu.INVALID_INPUT_MSG = ""
        sys.modules["utils.enhanced_evmenu"] = fake_evmenu
        fake_fusion = types.ModuleType("utils.fusion")
        fake_fusion.record_fusion = lambda *args, **kwargs: None
        sys.modules["utils.fusion"] = fake_fusion

        chargen = load_chargen_module()
        fused = types.SimpleNamespace(level=7, total_exp=1500, unique_id="uid")
        chargen._generate_instance = lambda *args, **kwargs: object()
        chargen._build_owned_pokemon = lambda *args, **kwargs: fused
        chargen.record_fusion = lambda *args, **kwargs: None

    finally:
        for name, module in patched.items():
            if module is not None:
                sys.modules[name] = module
            else:
                sys.modules.pop(name, None)

    class DummyCaller:
        def __init__(self):
            self.ndb = types.SimpleNamespace(
                chargen={
                    "player_gender": "M",
                    "species": "Pikachu",
                    "species_key": "pikachu",
                    "ability": "Static",
                    "nature": "Bold",
                }
            )
            self.db = types.SimpleNamespace()
            self.trainer = object()
            self.msgs = []

        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller()
    chargen.finish_fusion(caller, "")
    assert caller.db.level == fused.level
    assert caller.db.total_exp == fused.total_exp
