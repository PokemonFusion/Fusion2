import types
import sys


def load_display(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia_utils = types.ModuleType("evennia.utils")
    fake_evtable = types.ModuleType("evennia.utils.evtable")
    fake_ansi = types.ModuleType("evennia.utils.ansi")
    fake_utils = types.ModuleType("evennia.utils.utils")

    fake_evtable.EvTable = type("EvTable", (), {})
    fake_ansi.strip_ansi = lambda text: str(text)
    fake_utils.strip_ansi = lambda text: str(text)

    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    monkeypatch.setitem(sys.modules, "evennia.utils", fake_evennia_utils)
    monkeypatch.setitem(sys.modules, "evennia.utils.evtable", fake_evtable)
    monkeypatch.setitem(sys.modules, "evennia.utils.ansi", fake_ansi)
    monkeypatch.setitem(sys.modules, "evennia.utils.utils", fake_utils)
    sys.modules.pop("utils.display", None)

    from utils.display import display_trainer_sheet

    return display_trainer_sheet


class Attrs:
    def get(self, _key, default=None):
        return default


def test_trainer_sheet_shows_trainer_level_and_txp(monkeypatch):
    display_trainer_sheet = load_display(monkeypatch)
    char = types.SimpleNamespace(
        key="Trainer",
        db=types.SimpleNamespace(trainer_xp=40, inventory={}),
        attributes=Attrs(),
    )

    sheet = display_trainer_sheet(char, mode="brief")

    assert "Trainer" in sheet
    assert "TXP" in sheet
    assert "40" in sheet
