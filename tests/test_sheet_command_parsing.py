import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_cmd_module(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)

    monkeypatch.setitem(sys.modules, "pokemon", types.ModuleType("pokemon"))
    monkeypatch.setitem(sys.modules, "pokemon.helpers", types.ModuleType("pokemon.helpers"))

    fake_party_helpers = types.ModuleType("pokemon.helpers.party_helpers")
    fake_party_helpers.get_active_party = lambda caller: []
    monkeypatch.setitem(sys.modules, "pokemon.helpers.party_helpers", fake_party_helpers)

    fake_pokemon_helpers = types.ModuleType("pokemon.helpers.pokemon_helpers")
    fake_pokemon_helpers.get_max_hp = lambda mon: 0
    fake_pokemon_helpers.get_stats = lambda mon: {}
    monkeypatch.setitem(sys.modules, "pokemon.helpers.pokemon_helpers", fake_pokemon_helpers)

    monkeypatch.setitem(sys.modules, "pokemon.models", types.ModuleType("pokemon.models"))
    fake_stats = types.ModuleType("pokemon.models.stats")
    fake_stats.level_for_exp = lambda xp, growth: xp
    monkeypatch.setitem(sys.modules, "pokemon.models.stats", fake_stats)

    monkeypatch.setitem(sys.modules, "utils", types.ModuleType("utils"))
    fake_display = types.ModuleType("utils.display")
    fake_display.display_pokemon_sheet = lambda *args, **kwargs: "pokemon"
    fake_display.display_trainer_sheet = lambda *args, **kwargs: "trainer"
    monkeypatch.setitem(sys.modules, "utils.display", fake_display)

    fake_display_helpers = types.ModuleType("utils.display_helpers")
    fake_display_helpers.get_status_effects = lambda mon: "NRM"
    monkeypatch.setitem(sys.modules, "utils.display_helpers", fake_display_helpers)

    fake_xp = types.ModuleType("utils.xp_utils")
    fake_xp.get_display_xp = lambda mon: 0
    monkeypatch.setitem(sys.modules, "utils.xp_utils", fake_xp)

    path = os.path.join(ROOT, "commands", "player", "cmd_sheet.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_sheet_parse_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_sheet_command_parses_slash_variants(monkeypatch):
    cmd_mod = load_cmd_module(monkeypatch)

    cmd = cmd_mod.CmdSheet()
    cmd.args = "/brief"
    cmd.parse()
    assert cmd.mode == "brief"
    assert not cmd.view_inventory
    assert cmd.args == ""

    cmd = cmd_mod.CmdSheet()
    cmd.args = "/inv 2"
    cmd.parse()
    assert cmd.mode == "full"
    assert cmd.view_inventory
    assert cmd.page == 2
    assert cmd.args == "2"

    cmd = cmd_mod.CmdSheet()
    cmd.args = "/inv find potion"
    cmd.parse()
    assert cmd.view_inventory
    assert cmd.find == "potion"

    cmd = cmd_mod.CmdSheet()
    cmd.args = "/inv/cat cols 4"
    cmd.parse()
    assert not cmd.view_inventory
    assert cmd.view_inventory_by_category
    assert cmd.cols == 4


def test_sheet_pokemon_command_parses_party_slash_variants(monkeypatch):
    cmd_mod = load_cmd_module(monkeypatch)

    cmd = cmd_mod.CmdSheetPokemon()
    cmd.args = "/brief 2"
    cmd.parse()
    assert cmd.mode == "brief"
    assert cmd.slot == 2
    assert not cmd.show_all

    cmd = cmd_mod.CmdSheetPokemon()
    cmd.args = "/moves all"
    cmd.parse()
    assert cmd.mode == "moves"
    assert cmd.slot is None
    assert cmd.show_all
