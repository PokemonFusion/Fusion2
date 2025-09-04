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


@pytest.mark.parametrize(
    "stats,hp,expected",
    [({"hp": 30}, 25, "HP 25/0"), (None, 25, "HP 25/0"), (None, None, "HP 0/0")],
)
def test_sheet_pokemon_fusion_slot_displays_level_and_hp(stats, hp, expected):
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
        store = {}

        def fake_get_stats(mon):
            if isinstance(mon, (str, bytes)):
                return store.get(mon, {})
            return getattr(mon, "_cached_stats", {})

        def fake_get_max_hp(mon):
            return fake_get_stats(mon).get("hp", 0)

        fake_helpers.get_max_hp = fake_get_max_hp
        fake_helpers.get_stats = fake_get_stats
        sys.modules["pokemon.helpers.pokemon_helpers"] = fake_helpers

        sys.modules["pokemon.models"] = types.ModuleType("pokemon.models")
        fake_stats = types.ModuleType("pokemon.models.stats")
        fake_stats.level_for_exp = lambda xp, growth: xp
        sys.modules["pokemon.models.stats"] = fake_stats

        sys.modules["utils"] = types.ModuleType("utils")
        fake_display = types.ModuleType("utils.display")

        captured_mon = {}

        def fake_display_pokemon_sheet(caller, mon, **kwargs):
            captured_mon["mon"] = mon
            hp_val = getattr(mon, "hp", 0)
            max_hp = fake_helpers.get_max_hp(mon)
            if max_hp <= 0:
                pass
            return "sheet"

        fake_display.display_pokemon_sheet = fake_display_pokemon_sheet
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
                fusion_id="fusion-uid",
                fusion_ability="Static",
                fusion_nature="Bold",
                level=10,
                hp=hp,
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

    caller.msgs = []
    cmd = cmd_mod.CmdSheetPokemon()
    cmd.caller = caller
    cmd.args = "1"
    cmd.switches = []
    cmd.parse()
    cmd.func()
    assert caller.msgs[-1].startswith("sheet")
    assert getattr(captured_mon.get("mon"), "unique_id", None) == caller.db.fusion_id


def test_sheet_pokemon_fusion_slot_falls_back_to_fused_stats():
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

    captured = {}
    store = {}

    try:
        fake_evennia = types.ModuleType("evennia")
        fake_evennia.Command = type("Command", (), {})
        sys.modules["evennia"] = fake_evennia

        sys.modules["pokemon"] = types.ModuleType("pokemon")
        sys.modules["pokemon.helpers"] = types.ModuleType("pokemon.helpers")
        fake_helpers = types.ModuleType("pokemon.helpers.pokemon_helpers")

        def fake_get_stats(mon):
            if isinstance(mon, (str, bytes)):
                return store.get(mon, {})
            return getattr(mon, "_cached_stats", {})

        def fake_get_max_hp(mon):
            return fake_get_stats(mon).get("hp", 0)

        fake_helpers.get_max_hp = fake_get_max_hp
        fake_helpers.get_stats = fake_get_stats
        sys.modules["pokemon.helpers.pokemon_helpers"] = fake_helpers

        sys.modules["pokemon.models"] = types.ModuleType("pokemon.models")
        fake_stats = types.ModuleType("pokemon.models.stats")
        fake_stats.level_for_exp = lambda xp, growth: xp
        sys.modules["pokemon.models.stats"] = fake_stats

        sys.modules["utils"] = types.ModuleType("utils")
        fake_display = types.ModuleType("utils.display")

        def fake_display_pokemon_sheet(caller, mon, **kwargs):
            captured["mon"] = mon
            captured["hp"] = getattr(mon, "hp", 0)
            captured["max_hp"] = fake_helpers.get_max_hp(getattr(mon, "unique_id", mon))
            return "sheet"

        fake_display.display_pokemon_sheet = fake_display_pokemon_sheet
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
        for name, module in patched.items():
            if module is not None:
                sys.modules[name] = module
            else:
                sys.modules.pop(name, None)

    fused = types.SimpleNamespace(
        species="Pikachu",
        hp=20,
        _cached_stats={"hp": 40},
        activemoveslot_set=[],
        pp_bonuses={},
        moves=[],
        ivs=[],
        evs=[],
        unique_id="fusion-uid",
    )
    store[fused.unique_id] = fused._cached_stats

    class DummyStorage:
        def get_party(self):
            return []

        active_pokemon = types.SimpleNamespace(all=lambda: [fused])

    class DummyCaller:
        def __init__(self):
            self.key = "Ash"
            self.db = types.SimpleNamespace(
                fusion_species="Pikachu",
                fusion_id=fused.unique_id,
                fusion_ability="Static",
                fusion_nature="Bold",
                level=10,
                hp=None,
                stats=None,
                gender="M",
            )
            self.storage = DummyStorage()
            self.msgs = []

        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller()

    cmd = cmd_mod.CmdSheetPokemon()
    cmd.caller = caller
    cmd.args = "1"
    cmd.switches = []
    cmd.parse()
    cmd.func()

    assert captured["hp"] == 20
    assert captured["max_hp"] == 40
    assert getattr(captured.get("mon"), "unique_id", None) == fused.unique_id
    assert fake_helpers.get_stats(captured["mon"].unique_id)["hp"] == 40


def test_sheet_pokemon_fusion_slot_computes_stats_without_cache():
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

    captured = {}

    fused = types.SimpleNamespace(
        species="Pikachu",
        hp=20,
        activemoveslot_set=[],
        pp_bonuses={},
        moves=[],
        ivs=[],
        evs=[],
        unique_id="fusion-uid",
    )

    expected_stats = {
        "hp": 40,
        "attack": 1,
        "defense": 2,
        "sp_attack": 3,
        "sp_defense": 4,
        "speed": 5,
    }

    try:
        fake_evennia = types.ModuleType("evennia")
        fake_evennia.Command = type("Command", (), {})
        sys.modules["evennia"] = fake_evennia

        sys.modules["pokemon"] = types.ModuleType("pokemon")
        sys.modules["pokemon.helpers"] = types.ModuleType("pokemon.helpers")
        fake_helpers = types.ModuleType("pokemon.helpers.pokemon_helpers")

        def fake_get_stats(mon):
            if mon is fused:
                return expected_stats
            if isinstance(mon, (str, bytes)):
                return {"hp": expected_stats["hp"]} if mon == fused.unique_id else {}
            return getattr(mon, "_cached_stats", {})

        def fake_get_max_hp(mon):
            return fake_get_stats(mon).get("hp", 0)

        fake_helpers.get_max_hp = fake_get_max_hp
        fake_helpers.get_stats = fake_get_stats
        sys.modules["pokemon.helpers.pokemon_helpers"] = fake_helpers

        sys.modules["pokemon.models"] = types.ModuleType("pokemon.models")
        fake_stats = types.ModuleType("pokemon.models.stats")
        fake_stats.level_for_exp = lambda xp, growth: xp
        sys.modules["pokemon.models.stats"] = fake_stats

        sys.modules["utils"] = types.ModuleType("utils")
        fake_display = types.ModuleType("utils.display")

        def fake_display_pokemon_sheet(caller, mon, **kwargs):
            captured["mon"] = mon
            captured["max_hp"] = fake_helpers.get_max_hp(mon)
            return "sheet"

        fake_display.display_pokemon_sheet = fake_display_pokemon_sheet
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
        for name, module in patched.items():
            if module is not None:
                sys.modules[name] = module
            else:
                sys.modules.pop(name, None)

    class DummyStorage:
        def get_party(self):
            return []

        active_pokemon = types.SimpleNamespace(all=lambda: [fused])

    class DummyCaller:
        def __init__(self):
            self.key = "Ash"
            self.db = types.SimpleNamespace(
                fusion_species="Pikachu",
                fusion_id=fused.unique_id,
                fusion_ability="Static",
                fusion_nature="Bold",
                level=10,
                hp=None,
                stats=None,
                gender="M",
            )
            self.storage = DummyStorage()
            self.msgs = []

        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller()

    cmd = cmd_mod.CmdSheetPokemon()
    cmd.caller = caller
    cmd.args = "1"
    cmd.switches = []
    cmd.parse()
    cmd.func()

    assert captured["max_hp"] == 40
    stats_dict = fake_helpers.get_stats(captured["mon"])
    assert set(stats_dict) == {"hp", "attack", "defense", "sp_attack", "sp_defense", "speed"}
