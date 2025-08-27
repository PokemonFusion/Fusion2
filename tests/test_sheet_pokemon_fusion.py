"""Tests for the +sheet/pokemon command when handling fusions."""

import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    """Dynamically load the sheet command module."""
    path = os.path.join(ROOT, "commands", "player", "cmd_sheet.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_sheet", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_sheet_pokemon_lists_fusion():
        """Ensure fusions are labeled and include the trainer name."""
        # Preserve any real modules to restore later
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

        # Stub required modules
        evennia_mod = types.ModuleType("evennia")
        evennia_mod.Command = type("Command", (), {})
        sys.modules["evennia"] = evennia_mod

        pokemon_pkg = types.ModuleType("pokemon")
        pokemon_pkg.__path__ = []
        sys.modules["pokemon"] = pokemon_pkg
        helpers_pkg = types.ModuleType("pokemon.helpers")
        helpers_pkg.__path__ = []
        sys.modules["pokemon.helpers"] = helpers_pkg
        helpers_mod = types.ModuleType("pokemon.helpers.pokemon_helpers")
        helpers_mod.get_max_hp = lambda mon: getattr(mon, "max_hp", 1)
        sys.modules["pokemon.helpers.pokemon_helpers"] = helpers_mod
        models_pkg = types.ModuleType("pokemon.models")
        models_pkg.__path__ = []
        sys.modules["pokemon.models"] = models_pkg
        stats_mod = types.ModuleType("pokemon.models.stats")
        stats_mod.level_for_exp = lambda xp, growth: xp
        sys.modules["pokemon.models.stats"] = stats_mod
        fusion_models_mod = types.ModuleType("pokemon.models.fusion")

        class FakeManager:
                def __init__(self):
                        self.store = []

                def filter(self, **kwargs):
                        trainer = kwargs.get("trainer")
                        items = [e for e in self.store if e.trainer is trainer]

                        class _QS(list):
                                def first(self_inner):
                                        return self_inner[0] if self_inner else None

                        return _QS(items)

        class FakePokemonFusion:
                objects = FakeManager()

                def __init__(self, trainer=None, pokemon=None, result=None):
                        self.trainer = trainer
                        self.pokemon = pokemon
                        self.result = result

        fusion_models_mod.PokemonFusion = FakePokemonFusion
        sys.modules["pokemon.models.fusion"] = fusion_models_mod
        models_pkg.fusion = fusion_models_mod

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

        cmd_mod = load_cmd_module()

        # Restore real modules
        if orig_evennia is not None:
                sys.modules["evennia"] = orig_evennia
        else:
                sys.modules.pop("evennia", None)
        if orig_pokemon is not None:
                sys.modules["pokemon"] = orig_pokemon
        else:
                sys.modules.pop("pokemon", None)
        if orig_helpers_pkg is not None:
                sys.modules["pokemon.helpers"] = orig_helpers_pkg
        else:
                sys.modules.pop("pokemon.helpers", None)
        if orig_pokemon_helpers is not None:
                sys.modules["pokemon.helpers.pokemon_helpers"] = orig_pokemon_helpers
        else:
                sys.modules.pop("pokemon.helpers.pokemon_helpers", None)
        if orig_models_pkg is not None:
                sys.modules["pokemon.models"] = orig_models_pkg
        else:
                sys.modules.pop("pokemon.models", None)
        if orig_stats is not None:
                sys.modules["pokemon.models.stats"] = orig_stats
        else:
                sys.modules.pop("pokemon.models.stats", None)
        if orig_utils_pkg is not None:
                sys.modules["utils"] = orig_utils_pkg
        else:
                sys.modules.pop("utils", None)
        if orig_utils_display is not None:
                sys.modules["utils.display"] = orig_utils_display
        else:
                sys.modules.pop("utils.display", None)
        if orig_utils_display_helpers is not None:
                sys.modules["utils.display_helpers"] = orig_utils_display_helpers
        else:
                sys.modules.pop("utils.display_helpers", None)
        if orig_utils_xp_utils is not None:
                sys.modules["utils.xp_utils"] = orig_utils_xp_utils
        else:
                sys.modules.pop("utils.xp_utils", None)
        if orig_models_fusion is not None:
                sys.modules["pokemon.models.fusion"] = orig_models_fusion
        else:
                sys.modules.pop("pokemon.models.fusion", None)

        # Prepare dummy data
        class DummyMon:
                def __init__(self, name, species):
                        self.name = name
                        self.species = species
                        self.level = 5
                        self.hp = 10
                        self.max_hp = 20
                        self.gender = "M"

        fused_mon = DummyMon("Pikachu", "Pikachu")
        other_mon = DummyMon("Eevee", "Eevee")

        class DummyStorage:
                def get_party(self):
                        return [other_mon, fused_mon]

        class DummyCaller:
                        key = "Ash"
                        storage = DummyStorage()
                        msgs = []

                        def msg(self, text):
                                self.msgs.append(text)

        caller = DummyCaller()

        fused_mon.fusion_result = types.SimpleNamespace(trainer=caller)

        cmd = cmd_mod.CmdSheetPokemon()
        cmd.caller = caller
        cmd.args = ""
        cmd.switches = []
        cmd.parse()
        cmd.func()

        output = caller.msgs[-1]
        assert "Ash (Pikachu) (fusion)" in output


def test_sheet_pokemon_lists_fusion_without_utils():
        """Fused Pokémon shows even if fusion utilities are missing."""
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

        evennia_mod = types.ModuleType("evennia")
        evennia_mod.Command = type("Command", (), {})
        sys.modules["evennia"] = evennia_mod

        pokemon_pkg = types.ModuleType("pokemon")
        pokemon_pkg.__path__ = []
        sys.modules["pokemon"] = pokemon_pkg
        helpers_pkg = types.ModuleType("pokemon.helpers")
        helpers_pkg.__path__ = []
        sys.modules["pokemon.helpers"] = helpers_pkg
        helpers_mod = types.ModuleType("pokemon.helpers.pokemon_helpers")
        helpers_mod.get_max_hp = lambda mon: getattr(mon, "max_hp", 1)
        sys.modules["pokemon.helpers.pokemon_helpers"] = helpers_mod
        models_pkg = types.ModuleType("pokemon.models")
        models_pkg.__path__ = []
        sys.modules["pokemon.models"] = models_pkg
        stats_mod = types.ModuleType("pokemon.models.stats")
        stats_mod.level_for_exp = lambda xp, growth: xp
        sys.modules["pokemon.models.stats"] = stats_mod
        fusion_models_mod = types.ModuleType("pokemon.models.fusion")

        class FakeManager:
                def __init__(self):
                        self.store = []

                def filter(self, **kwargs):
                        trainer = kwargs.get("trainer")
                        items = [e for e in self.store if e.trainer is trainer]

                        class _QS(list):
                                def first(self_inner):
                                        return self_inner[0] if self_inner else None

                        return _QS(items)

        class FakePokemonFusion:
                objects = FakeManager()

                def __init__(self, trainer=None, pokemon=None, result=None):
                        self.trainer = trainer
                        self.pokemon = pokemon
                        self.result = result

        fusion_models_mod.PokemonFusion = FakePokemonFusion
        sys.modules["pokemon.models.fusion"] = fusion_models_mod
        models_pkg.fusion = fusion_models_mod

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

        cmd_mod = load_cmd_module()

        if orig_evennia is not None:
                sys.modules["evennia"] = orig_evennia
        else:
                sys.modules.pop("evennia", None)
        if orig_pokemon is not None:
                sys.modules["pokemon"] = orig_pokemon
        else:
                sys.modules.pop("pokemon", None)
        if orig_helpers_pkg is not None:
                sys.modules["pokemon.helpers"] = orig_helpers_pkg
        else:
                sys.modules.pop("pokemon.helpers", None)
        if orig_pokemon_helpers is not None:
                sys.modules["pokemon.helpers.pokemon_helpers"] = orig_pokemon_helpers
        else:
                sys.modules.pop("pokemon.helpers.pokemon_helpers", None)
        if orig_models_pkg is not None:
                sys.modules["pokemon.models"] = orig_models_pkg
        else:
                sys.modules.pop("pokemon.models", None)
        if orig_stats is not None:
                sys.modules["pokemon.models.stats"] = orig_stats
        else:
                sys.modules.pop("pokemon.models.stats", None)
        if orig_utils_pkg is not None:
                sys.modules["utils"] = orig_utils_pkg
        else:
                sys.modules.pop("utils", None)
        if orig_utils_display is not None:
                sys.modules["utils.display"] = orig_utils_display
        else:
                sys.modules.pop("utils.display", None)
        if orig_utils_display_helpers is not None:
                sys.modules["utils.display_helpers"] = orig_utils_display_helpers
        else:
                sys.modules.pop("utils.display_helpers", None)
        if orig_utils_xp_utils is not None:
                sys.modules["utils.xp_utils"] = orig_utils_xp_utils
        else:
                sys.modules.pop("utils.xp_utils", None)
        if orig_models_fusion is not None:
                sys.modules["pokemon.models.fusion"] = orig_models_fusion
        else:
                sys.modules.pop("pokemon.models.fusion", None)

        class DummyMon:
                def __init__(self, name, species):
                        self.name = name
                        self.species = species
                        self.level = 5
                        self.hp = 10
                        self.max_hp = 20
                        self.gender = "M"

        fused_mon = DummyMon("Pikachu", "Pikachu")
        other_mon = DummyMon("Eevee", "Eevee")

        class DummyStorage:
                def get_party(self):
                        return [other_mon]

        class DummyTrainer:
                key = "Ash"

        class DummyCaller:
                        key = "Ash"
                        storage = DummyStorage()
                        trainer = DummyTrainer()
                        msgs = []

                        def msg(self, text):
                                self.msgs.append(text)

        caller = DummyCaller()

        fusion_entry = cmd_mod.PokemonFusion(trainer=caller.trainer, pokemon=other_mon, result=fused_mon)
        cmd_mod.PokemonFusion.objects.store.append(fusion_entry)
        fused_mon.fusion_result = fusion_entry

        cmd = cmd_mod.CmdSheetPokemon()
        cmd.caller = caller
        cmd.args = ""
        cmd.switches = []
        cmd.parse()
        cmd.func()

        output = caller.msgs[-1]
        assert "Ash (Pikachu) (fusion)" in output

