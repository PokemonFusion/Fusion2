"""Tests for the +sheet/pokemon command when handling fusions."""

import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_module(path, name):
    """Dynamically load a module from ``path`` under ``name``."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_sheet_pokemon_lists_fusion_for_new_trainer():
    """Ensure fusions are created during chargen and listed on the sheet."""

    # Preserve real modules so we can restore them later
    orig_evennia = sys.modules.get("evennia")
    orig_pokemon = sys.modules.get("pokemon")
    orig_helpers_pkg = sys.modules.get("pokemon.helpers")
    orig_pokemon_helpers = sys.modules.get("pokemon.helpers.pokemon_helpers")
    orig_models_pkg = sys.modules.get("pokemon.models")
    orig_stats = sys.modules.get("pokemon.models.stats")
    orig_utils_pkg = sys.modules.get("utils")
    orig_utils_display = sys.modules.get("utils.display")
    orig_utils_display_helpers = sys.modules.get("utils.display_helpers")
    orig_utils_xp_utils = sys.modules.get("utils.xp_utils")
    orig_models_fusion = sys.modules.get("pokemon.models.fusion")
    orig_data_generation = sys.modules.get("pokemon.data.generation")
    orig_data_starters = sys.modules.get("pokemon.data.starters")
    orig_dex = sys.modules.get("pokemon.dex")
    orig_models_storage = sys.modules.get("pokemon.models.storage")

    try:
        # ------------------------------------------------------------------
        # Stub required modules
        # ------------------------------------------------------------------
        evennia_mod = types.ModuleType("evennia")
        evennia_mod.Command = type("Command", (), {})
        sys.modules["evennia"] = evennia_mod

        pokemon_pkg = types.ModuleType("pokemon")
        pokemon_pkg.__path__ = []
        sys.modules["pokemon"] = pokemon_pkg

        helpers_pkg = types.ModuleType("pokemon.helpers")
        helpers_pkg.__path__ = []
        sys.modules["pokemon.helpers"] = helpers_pkg

        class DummyMon:
            def __init__(self, name):
                self.name = name
                self.species = name
                self.level = 5
                self.hp = 10
                self.max_hp = 20
                self.gender = "M"
                self.id = 1
                self.in_party = False

        def create_owned_pokemon(species, trainer, level, **kwargs):
            return DummyMon(species)

        helpers_mod = types.ModuleType("pokemon.helpers.pokemon_helpers")
        helpers_mod.get_max_hp = lambda mon: mon.max_hp
        helpers_mod.create_owned_pokemon = create_owned_pokemon
        sys.modules["pokemon.helpers.pokemon_helpers"] = helpers_mod

        data_pkg = types.ModuleType("pokemon.data")
        data_pkg.__path__ = []
        sys.modules["pokemon.data"] = data_pkg

        gen_mod = types.ModuleType("pokemon.data.generation")
        gen_mod.NATURES = {"Hardy": None}

        ivs_obj = types.SimpleNamespace(
            hp=0, attack=0, defense=0, special_attack=0, special_defense=0, speed=0
        )

        def generate_pokemon(key, level):
            return types.SimpleNamespace(
                species=types.SimpleNamespace(name="Pikachu"),
                ability="Static",
                ivs=ivs_obj,
                gender="M",
                nature="Hardy",
            )

        gen_mod.generate_pokemon = generate_pokemon
        sys.modules["pokemon.data.generation"] = gen_mod
        data_pkg.generation = gen_mod

        starters_mod = types.ModuleType("pokemon.data.starters")
        starters_mod.STARTER_LOOKUP = {}
        starters_mod.get_starter_names = lambda: []
        sys.modules["pokemon.data.starters"] = starters_mod
        data_pkg.starters = starters_mod

        dex_mod = types.ModuleType("pokemon.dex")
        dex_mod.POKEDEX = {
            "pikachu": types.SimpleNamespace(raw={"name": "Pikachu"}, name="Pikachu")
        }
        sys.modules["pokemon.dex"] = dex_mod

        models_pkg = types.ModuleType("pokemon.models")
        models_pkg.__path__ = []
        sys.modules["pokemon.models"] = models_pkg

        stats_mod = types.ModuleType("pokemon.models.stats")
        stats_mod.level_for_exp = lambda xp, growth: xp
        sys.modules["pokemon.models.stats"] = stats_mod

        storage_mod = types.ModuleType("pokemon.models.storage")
        storage_mod.ensure_boxes = lambda s: s
        sys.modules["pokemon.models.storage"] = storage_mod
        models_pkg.storage = storage_mod

        class FakeManager:
            def __init__(self):
                self.store = []

            def get_or_create(self, defaults=None, **kwargs):
                trainer = kwargs.get("trainer")
                pokemon = kwargs.get("pokemon")
                defaults = defaults or {}
                for obj in self.store:
                    if obj.trainer is trainer and obj.pokemon is pokemon:
                        return obj, False
                obj = FakePokemonFusion(
                    trainer=trainer,
                    pokemon=pokemon,
                    result=defaults.get("result"),
                    permanent=defaults.get("permanent", False),
                )
                self.store.append(obj)
                return obj, True

            def filter(self, **kwargs):
                trainer = kwargs.get("trainer")
                items = [e for e in self.store if e.trainer is trainer]

                class _QS(list):
                    def first(self_inner):
                        return self_inner[0] if self_inner else None

                return _QS(items)

        class FakePokemonFusion:
            objects = FakeManager()

            def __init__(self, trainer=None, pokemon=None, result=None, permanent=False):
                self.trainer = trainer
                self.pokemon = pokemon
                self.result = result
                self.permanent = permanent
                if result:
                    setattr(result, "fusion_result", self)

        fusion_mod = types.ModuleType("pokemon.models.fusion")
        fusion_mod.PokemonFusion = FakePokemonFusion
        sys.modules["pokemon.models.fusion"] = fusion_mod
        models_pkg.fusion = fusion_mod

        utils_pkg = types.ModuleType("utils")
        sys.modules["utils"] = utils_pkg

        display_mod = types.ModuleType("utils.display")
        display_mod.display_pokemon_sheet = lambda *a, **k: ""
        display_mod.display_trainer_sheet = lambda *a, **k: ""
        sys.modules["utils.display"] = display_mod
        utils_pkg.display = display_mod

        display_helpers_mod = types.ModuleType("utils.display_helpers")
        display_helpers_mod.get_status_effects = lambda mon: "OK"
        sys.modules["utils.display_helpers"] = display_helpers_mod
        utils_pkg.display_helpers = display_helpers_mod

        xp_utils_mod = types.ModuleType("utils.xp_utils")
        xp_utils_mod.get_display_xp = lambda mon: 0
        sys.modules["utils.xp_utils"] = xp_utils_mod
        utils_pkg.xp_utils = xp_utils_mod

        # Load utils.fusion so chargen can record fusions
        spec_fusion = importlib.util.spec_from_file_location(
            "utils.fusion", os.path.join(ROOT, "utils", "fusion.py")
        )
        fusion_utils = importlib.util.module_from_spec(spec_fusion)
        sys.modules[spec_fusion.name] = fusion_utils
        spec_fusion.loader.exec_module(fusion_utils)
        utils_pkg.fusion = fusion_utils

        # Load target modules
        cmd_mod = load_module(
            os.path.join(ROOT, "commands", "player", "cmd_sheet.py"),
            "commands.player.cmd_sheet",
        )
        chargen_mod = load_module(
            os.path.join(ROOT, "menus", "chargen.py"), "menus.chargen"
        )

        # ------------------------------------------------------------------
        # Create a fused trainer via chargen
        # ------------------------------------------------------------------
        class DummyStorage:
            def __init__(self):
                self.party = []

            def add_active_pokemon(self, mon):
                self.party.append(mon)

            def get_party(self):
                return list(self.party)

        storage = DummyStorage()
        trainer = types.SimpleNamespace(user=types.SimpleNamespace(storage=storage))
        caller = types.SimpleNamespace(
            key="Ash",
            storage=storage,
            trainer=trainer,
            ndb=types.SimpleNamespace(
                chargen={
                    "player_gender": "M",
                    "species_key": "pikachu",
                    "species": "Pikachu",
                    "ability": "Static",
                    "nature": "Hardy",
                }
            ),
            db=types.SimpleNamespace(),
            msgs=[],
        )
        caller.msg = lambda text: caller.msgs.append(text)

        chargen_mod.finish_fusion(caller, "")

        # Invoke the sheet command
        cmd = cmd_mod.CmdSheetPokemon()
        cmd.caller = caller
        cmd.args = ""
        cmd.switches = []
        cmd.parse()
        cmd.func()

        output = caller.msgs[-1]
        assert "Ash (Pikachu) (fusion)" in output
    finally:
        # ------------------------------------------------------------------
        # Restore modules
        # ------------------------------------------------------------------
        mapping = {
            "evennia": orig_evennia,
            "pokemon": orig_pokemon,
            "pokemon.helpers": orig_helpers_pkg,
            "pokemon.helpers.pokemon_helpers": orig_pokemon_helpers,
            "pokemon.models": orig_models_pkg,
            "pokemon.models.stats": orig_stats,
            "utils": orig_utils_pkg,
            "utils.display": orig_utils_display,
            "utils.display_helpers": orig_utils_display_helpers,
            "utils.xp_utils": orig_utils_xp_utils,
            "pokemon.models.fusion": orig_models_fusion,
            "pokemon.data.generation": orig_data_generation,
            "pokemon.data.starters": orig_data_starters,
            "pokemon.dex": orig_dex,
            "pokemon.models.storage": orig_models_storage,
        }
        for name, mod in mapping.items():
            if mod is not None:
                sys.modules[name] = mod
            else:
                sys.modules.pop(name, None)

