import sys
import os
import types
import importlib.util

# Stub minimal pokemon.stats before importing display utilities
_real_stats = sys.modules.get("pokemon.stats")
_real_dex = sys.modules.get("pokemon.dex")
_real_evennia = sys.modules.get("evennia")
_real_evennia_utils = sys.modules.get("evennia.utils")
_real_evennia_evtable = sys.modules.get("evennia.utils.evtable")

# Create minimal Evennia EvTable stub
evennia_evtable = types.ModuleType("evennia.utils.evtable")

class _EvTable:
    """Minimal stand-in for Evennia's EvTable used in tests."""

    def __init__(self, *_, **__):
        self._rows = []

    def add_row(self, *cols, **__):  # pragma: no cover - simple storage
        self._rows.append(cols)

    def __str__(self):  # pragma: no cover - simple representation
        return "\n".join(" ".join(str(c) for c in row) for row in self._rows)

evennia_evtable.EvTable = _EvTable
evennia_utils = types.ModuleType("evennia.utils")
evennia_utils.evtable = evennia_evtable
evennia_utils.ansi = types.SimpleNamespace(parse_ansi=lambda text: text)
evennia_mod = types.ModuleType("evennia")
evennia_mod.utils = evennia_utils
sys.modules["evennia"] = evennia_mod
sys.modules["evennia.utils"] = evennia_utils
sys.modules["evennia.utils.evtable"] = evennia_evtable

# Stub pokemon.dex with minimal MOVEDEX entries for PP lookup
pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.POKEDEX = {}
pokemon_dex.MOVEDEX = {
    "tackle": types.SimpleNamespace(pp=35),
    "ember": types.SimpleNamespace(pp=25),
}
# load real entities module for generation helpers
entities_path = os.path.join(os.path.dirname(__file__), "..", "pokemon", "dex", "entities.py")
spec = importlib.util.spec_from_file_location("pokemon.dex.entities", entities_path)
entities_mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = entities_mod
spec.loader.exec_module(entities_mod)  # type: ignore
pokemon_dex.entities = entities_mod
sys.modules["pokemon.dex"] = pokemon_dex

import pytest
import utils.display as display
from types import SimpleNamespace

# Restore original modules for other tests
if _real_stats is not None:
    sys.modules["pokemon.stats"] = _real_stats
else:
    del sys.modules["pokemon.stats"]
if _real_dex is not None:
    sys.modules["pokemon.dex"] = _real_dex
else:
    del sys.modules["pokemon.dex"]
if _real_evennia is not None:
    sys.modules["evennia"] = _real_evennia
else:
    del sys.modules["evennia"]
if _real_evennia_utils is not None:
    sys.modules["evennia.utils"] = _real_evennia_utils
else:
    del sys.modules["evennia.utils"]
if _real_evennia_evtable is not None:
    sys.modules["evennia.utils.evtable"] = _real_evennia_evtable
else:
    del sys.modules["evennia.utils.evtable"]


@pytest.fixture(autouse=True)
def patch_helpers(monkeypatch):
    """Patch helper functions to avoid heavy dependencies."""
    monkeypatch.setattr(display, "get_max_hp", lambda _p: 40)
    monkeypatch.setattr(
        display,
        "get_stats",
        lambda _p: {
            "hp": 40,
            "attack": 10,
            "defense": 10,
            "special_attack": 10,
            "special_defense": 10,
            "speed": 10,
        },
    )


class _Slot:
    def __init__(self, move, slot, current_pp):
        self.move = move
        self.slot = slot
        self.current_pp = current_pp


class _SlotManager:
    def __init__(self, slots):
        self._slots = slots

    def all(self):
        return self

    def order_by(self, field):
        return sorted(self._slots, key=lambda s: getattr(s, field))


class DummyPokemon:
    name = "Testmon"
    species = "Testmon"
    gender = "M"
    level = 5
    total_exp = 0
    current_hp = 30
    status = ""
    nature = "Hardy"
    ability = "Run Away"
    held_item = None
    pp_bonuses = {}

    def __init__(self):
        tackle = SimpleNamespace(name="Tackle")
        ember = SimpleNamespace(name="Ember")
        slots = [_Slot(tackle, 1, 20), _Slot(ember, 2, 10)]
        self.activemoveslot_set = _SlotManager(slots)


def test_sheet_displays_active_moves_with_pp():
    mon = DummyPokemon()
    sheet = display.display_pokemon_sheet(None, mon, slot=1)
    assert "Tackle (20/35 PP)" in sheet
    assert "Ember (10/25 PP)" in sheet


def test_iv_ev_breakdown_handles_lists():
    """_maybe_stat_breakdown should accept IV/EV data as lists."""
    mon = DummyPokemon()
    mon.ivs = [1, 2, 3, 4, 5, 6]
    mon.evs = [6, 5, 4, 3, 2, 1]
    table = display._maybe_stat_breakdown(mon)
    assert "IV" in table and "EV" in table
    assert "1" in table and "6" in table
