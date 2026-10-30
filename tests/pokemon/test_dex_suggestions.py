import sys
import types

from utils.dex_suggestions import (
	is_known_species,
	item_not_found_message,
	move_not_found_message,
	species_not_found_message,
)


def test_species_suggestion_prefers_entry_display_name(monkeypatch):
	fake_dex = types.ModuleType("pokemon.dex")
	fake_dex.POKEDEX = {
		"squirtle": types.SimpleNamespace(name="Squirtle"),
		"wartortle": types.SimpleNamespace(name="Wartortle"),
	}
	monkeypatch.setitem(sys.modules, "pokemon.dex", fake_dex)

	assert is_known_species("squirtle")
	assert species_not_found_message("Squirtel").endswith("Did you mean Squirtle?")


def test_move_and_item_messages_append_suggestions(monkeypatch):
	fake_dex = types.ModuleType("pokemon.dex")
	fake_dex.MOVEDEX = {"thunderbolt": types.SimpleNamespace(name="Thunderbolt")}
	fake_dex.ITEMDEX = {"potion": {"name": "Potion"}}
	monkeypatch.setitem(sys.modules, "pokemon.dex", fake_dex)

	assert move_not_found_message("Thundrbolt", "No move found.") == (
		"No move found. Did you mean Thunderbolt?"
	)
	assert item_not_found_message("Potoin", "No item found.") == (
		"No item found. Did you mean Potion?"
	)
