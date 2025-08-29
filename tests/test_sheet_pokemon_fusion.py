import importlib.util
import os
import sys
import types
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "player", "cmd_sheet.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_sheet", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("stats,expected", [({"hp": 30}, "HP 25/30"), (None, "HP 25/25")])
def test_sheet_pokemon_fusion_slot_displays_level_and_hp(stats, expected):
    # Preserve original modules
    patched = {
        "evennia": sys.modules.get("evennia"),
        "pokemon": sys.modules.get("pokemon"),
        "pokemon.helpers": sys.modules.get("pokemon.helpers"),
        "pokemon.helpers.pokemon_helpers": sys.modules.get("pokemon.helpers.pokemon_helpers"),
        "pokemon.models": sys.modules.get("pokemon.models"),
        "pokemon.models.stats": sys.modules.get("pokemon.models.stats"),
        "utils": sys.modules.get("utils"),
        "utils.display": sys.modules.get("utils.display"),
        "utils.display_helpers": sys.modules.get("utils.display_helpers"),
        "utils.xp_utils": sys.modules.get("utils.xp_utils"),
    }

    try:
        # Stub modules required by cmd_sheet
        fake_evennia = types.ModuleType("evennia")
        fake_evennia.Command = type("Command", (), {})
        sys.modules["evennia"] = fake_evennia

        sys.modules["pokemon"] = types.ModuleType("pokemon")
        sys.modules["pokemon.helpers"] = types.ModuleType("pokemon.helpers")
        fake_helpers = types.ModuleType("pokemon.helpers.pokemon_helpers")
        fake_helpers.get_max_hp = lambda mon: getattr(mon, "_cached_stats", {}).get("hp", 0)
        fake_helpers.get_stats = lambda mon: getattr(mon, "_cached_stats", {})
        sys.modules["pokemon.helpers.pokemon_helpers"] = fake_helpers

        sys.modules["pokemon.models"] = types.ModuleType("pokemon.models")
        fake_stats = types.ModuleType("pokemon.models.stats")
        fake_stats.level_for_exp = lambda xp, growth: xp
        sys.modules["pokemon.models.stats"] = fake_stats

        sys.modules["utils"] = types.ModuleType("utils")
        fake_display = types.ModuleType("utils.display")
        fake_display.display_pokemon_sheet = lambda *args, **kwargs: "sheet"
        fake_display.display_trainer_sheet = lambda *args, **kwargs: "trainer"
        sys.modules["utils.display"] = fake_display

        fake_disp_helpers = types.ModuleType("utils.display_helpers")
        fake_disp_helpers.get_status_effects = lambda mon: "NORM"
        sys.modules["utils.display_helpers"] = fake_disp_helpers

        fake_xp = types.ModuleType("utils.xp_utils")
        fake_xp.get_display_xp = lambda mon: 0
        sys.modules["utils.xp_utils"] = fake_xp

        cmd_mod = load_cmd_module()

    finally:
        # Restore original modules
        for name, module in patched.items():
            if module is not None:
                sys.modules[name] = module
            else:
                sys.modules.pop(name, None)

    class DummyStorage:
        def get_party(self):
            return []

        active_pokemon = types.SimpleNamespace(all=lambda: [])

    class DummyCaller:
        def __init__(self):
            self.key = "Ash"
            self.db = types.SimpleNamespace(
                fusion_species="Pikachu",
                fusion_ability="Static",
                fusion_nature="Bold",
                level=10,
                hp=25,
                stats=stats,
                gender="M",
            )
            self.storage = DummyStorage()
            self.msgs = []

        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller()
    cmd = cmd_mod.CmdSheetPokemon()
    cmd.caller = caller
    cmd.args = ""
    cmd.switches = []
    cmd.parse()
    cmd.func()

    assert caller.msgs, "No output captured"
    output = caller.msgs[-1]
    assert "Lv 10" in output
    assert expected in output
