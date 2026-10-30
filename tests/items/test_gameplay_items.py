"""Shared item metadata preserves names without allowing partial matches."""

import pytest

from pokemon.items import get_gameplay_item
from pokemon.middleware import get_item_by_name, get_item_description


@pytest.mark.parametrize("query,display", [
    ("Everstone", "Everstone"), ("EVER STONE", "Everstone"),
    ("blackaugurite", "Black Augurite"), ("Black Augurite", "Black Augurite"),
])
def test_supplemental_item_lookup_and_description(query, display):
    """Compact saved keys and complete display spelling share the same metadata."""
    _, item = get_item_by_name(query)
    assert item.name == display
    assert get_gameplay_item(query).name == display
    assert get_item_description(query, item) != "No description available."


@pytest.mark.parametrize("query", ["Ever", "Black", "Augurite", "unknown"])
def test_partial_or_unknown_gameplay_items_rejected(query):
    """Supplemental names do not loosen the command's exact-name boundary."""
    assert get_gameplay_item(query) is None
    assert get_item_by_name(query) == (None, None)
