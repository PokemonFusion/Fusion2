import sys
import types
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Stub evennia utils
ansi_mod = types.SimpleNamespace(strip_ansi=lambda s: s)
utils_mod = types.ModuleType("evennia.utils")
utils_mod.ansi = ansi_mod
sys.modules["evennia.utils"] = utils_mod
sys.modules["evennia.utils.ansi"] = ansi_mod

from pokemon.ui.move_gui import render_move_gui


def test_move_gui_lookup_and_formatting():
    slots = ["tackle", "ember", "growl", "thunderwave"]
    out = render_move_gui(slots, pp_overrides={0: 20})

    # Tackle: Normal type, PP override applied
    assert "|wNormal|n" in out
    assert "PP: 20/35" in out
    assert "Power: 40   Accuracy: 100" in out

    # Ember: Fire type
    assert "|rFire|n" in out
    assert "PP: 25/25" in out

    # Growl: status move should show dash for power
    assert "Power: —   Accuracy: 100" in out

    # Thunder Wave: Electric type, accuracy 90
    assert "|yElectric|n" in out
    assert "Power: —   Accuracy: 90" in out


def test_move_gui_object_fallback():
    """Objects lacking stats should be enriched from the movedex."""

    class Dummy:
        def __init__(self, name):
            self.name = name

    slots = [Dummy("tackle"), None, None, None]
    out = render_move_gui(slots)

    # Lookup should populate type, power and accuracy
    assert "|wNormal|n" in out
    assert "Power: 40   Accuracy: 100" in out
