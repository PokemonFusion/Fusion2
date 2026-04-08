"""Tests for dependency adapter fallback behavior."""

from __future__ import annotations

import sys
import types

from pokemon.utils.dependency_adapters import get_dex_data


def test_get_dex_data_continues_fallback_when_stubbed_dex_is_empty():
    """An empty dex stub should not block later dex-loading fallbacks."""

    original_dex = sys.modules.get("pokemon.dex")
    try:
        stub_dex = types.ModuleType("pokemon.dex")
        stub_dex.POKEDEX = {}
        stub_dex.MOVEDEX = {}
        sys.modules["pokemon.dex"] = stub_dex

        data = get_dex_data()
        assert isinstance(data["pokedex"], dict)
        assert data["pokedex"]
    finally:
        if original_dex is None:
            sys.modules.pop("pokemon.dex", None)
        else:
            sys.modules["pokemon.dex"] = original_dex
