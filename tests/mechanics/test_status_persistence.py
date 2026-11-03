"""Durable conditions exclude battle-only effects and have finite sleep."""

from types import SimpleNamespace

import pytest

from pokemon.services.status_persistence import PersistentStatus


@pytest.mark.parametrize("status", [0, None, "", "0", "confusion", "fnt"])
def test_only_major_conditions_are_durable(status):
    """Volatile conditions and legacy empty values never become saved status."""
    assert PersistentStatus.from_pokemon(SimpleNamespace(status=status)) == PersistentStatus()


def test_durable_sleep_excludes_source_and_volatile_state():
    """Saving sleep copies its remaining duration, not effect objects."""
    pokemon = SimpleNamespace(
        status="slp", tempvals={"sleep_turns": 0, "protect": 1},
        status_state={"source": object()}, volatiles={"confusion": 3},
    )
    state = PersistentStatus.from_pokemon(pokemon, battle=True)
    assert state == PersistentStatus("slp", 0)
    restored = SimpleNamespace(tempvals={})
    state.apply_to_battle(restored)
    assert restored.tempvals == {"sleep_turns": 0}
    assert restored.status_state == {"id": "slp"}


def test_legacy_sleep_without_counter_is_finite():
    """Incomplete adapters cannot leave a Pokémon asleep indefinitely."""
    assert PersistentStatus.from_pokemon(SimpleNamespace(status="slp")).sleep_turns == 1
