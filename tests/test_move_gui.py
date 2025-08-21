import os
import sys
import types
from typing import Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Stub evennia utils
ansi_mod = types.SimpleNamespace(strip_ansi=lambda s: s)
utils_mod = types.ModuleType("evennia.utils")
utils_mod.ansi = ansi_mod
sys.modules["evennia.utils"] = utils_mod
sys.modules["evennia.utils.ansi"] = ansi_mod

from pokemon.ui.move_gui import render_move_gui


def _row_heights(out: str) -> Tuple[int, int]:
	"""Return the number of lines in each move row (top, bottom)."""
	lines = out.splitlines()
	# Exclude prompt line at end
	content = lines[:-1]
	first_bottom = next(i for i, ln in enumerate(content) if ln.startswith("\\"))
	row1 = first_bottom + 1
	second_bottom_rel = next(i for i, ln in enumerate(content[first_bottom + 1 :]) if ln.startswith("\\"))
	row2 = second_bottom_rel + 1
	return row1, row2


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
	# Short descriptions should be shown
	assert "No additional effect." in out
	assert "10% chance to burn the target." in out


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
	assert "No additional effect." in out


def test_move_gui_wraps_long_descriptions():
	"""Long short descriptions should wrap across multiple lines."""

	slots = ["coreenforcer", None, None, None]
	out = render_move_gui(slots)

	assert "Nullifies the foe(s) Ability if" in out
	assert "the foe(s) move first." in out


def test_move_gui_trims_blank_description_lines():
	"""Rows should only be as tall as needed for their descriptions."""

	slots = ["tackle", "ember", "growl", "thunderwave"]
	out = render_move_gui(slots)
	row1, row2 = _row_heights(out)
	assert row1 == 7
	assert row2 == 7


def test_move_gui_expands_rows_per_pair():
	"""Rows expand to fit the longest description among their pair."""

	slots = ["coreenforcer", "tackle", None, None]
	out = render_move_gui(slots)
	row1, row2 = _row_heights(out)
	assert row1 == 8  # core enforcer spans two lines
	assert row2 == 7  # bottom row only needs one line
