"""Only the reviewed authored tuple can create an item-bearing wild encounter."""

from types import SimpleNamespace

import pytest

from pokemon.services.wild_held_items import WildHeldItems


@pytest.mark.parametrize("species,item,chance,roll,expected", [
    ("Rattata", "Oran Berry", 5, 5, "Oran Berry"), ("Rattata", "ORAN-BERRY", 100, 100, "Oran Berry"),
    ("Rattata", "Oran Berry", 5, 6, ""), ("Rattata", "Oran Berry", 0, 1, ""),
    ("Rattata-Alola", "Oran Berry", 100, 1, ""), ("Pikachu", "Oran Berry", 100, 1, ""),
    ("Rattata", "Pecha Berry", 100, 1, ""), ("Rattata", "Leader's Crest", 100, 1, ""),
    ("Rattata", "Mega Ring", 100, 1, ""), ("Rattata", "Oran", 100, 1, ""),
    ("Rattata", "Oran Berry", True, 1, ""), ("Rattata", "Oran Berry", "100", 1, ""),
    ("Rattata", "Oran Berry", -1, 1, ""), ("Rattata", "Oran Berry", 101, 1, ""),
])
def test_explicit_source_and_probability_boundaries(species, item, chance, roll, expected):
    """Defaults, malformed/excluded entries and failed rolls all stay empty."""
    assert WildHeldItems.select(species, {"held_item": item, "held_item_chance": chance},
                                SimpleNamespace(randint=lambda low, high: roll)) == expected


def test_missing_chance_never_implicitly_grants_held_item():
    """An older chart's item label alone is deliberately not an acquisition source."""
    assert WildHeldItems.select("Rattata", {"held_item": "Oran Berry"},
                                SimpleNamespace(randint=lambda *args: 1)) == ""
