"""Tests for Pokémon stat caching and recalculation."""

import types

import pokemon.utils.pokemon_helpers as helpers
from pokemon.stats import add_evs, add_experience, exp_for_level


def test_cached_stats_refresh_on_changes(monkeypatch):
    """Stat cache is reused and refreshed after EV or level changes."""

    call_count = {"count": 0}

    def fake_calculate(species, level, ivs, evs, nature):
        call_count["count"] += 1
        return {
            "hp": level + 10,
            "attack": level + evs.get("attack", 0) // 4,
            "defense": 1,
            "special_attack": 0,
            "special_defense": 0,
            "speed": 0,
        }

    monkeypatch.setattr(helpers, "calculate_stats", fake_calculate)

    mon = types.SimpleNamespace(
        species="Testmon",
        level=1,
        ivs={
            "hp": 0,
            "attack": 0,
            "defense": 0,
            "special_attack": 0,
            "special_defense": 0,
            "speed": 0,
        },
        evs={},
        nature="Hardy",
        total_exp=0,
    )

    first = helpers.get_stats(mon)
    assert call_count["count"] == 1
    assert first["attack"] == 1

    second = helpers.get_stats(mon)
    assert call_count["count"] == 1
    assert second is first

    add_evs(mon, {"atk": 4})
    after_ev = helpers.get_stats(mon)
    assert call_count["count"] == 2
    assert after_ev["attack"] == 2

    add_experience(mon, exp_for_level(2))
    after_level = helpers.get_stats(mon)
    assert call_count["count"] == 3
    assert mon.level == 2
    assert after_level["hp"] == 12
