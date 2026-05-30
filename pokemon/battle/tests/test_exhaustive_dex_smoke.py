"""Optional exhaustive dex smoke tests for non-manual battle validation."""

from __future__ import annotations

import copy

import pytest

from pokemon.battle.callbacks import resolve_callback_from_modules

from .outcome_harness import build_outcome_battle, pokemon_spec_from_dex

pytestmark = pytest.mark.dex


def _dex_data():
    import pokemon.dex as dex_mod  # type: ignore

    return dex_mod.ITEMDEX, dex_mod.POKEDEX


ITEM_CASES = sorted(_dex_data()[0].items(), key=lambda pair: pair[0])
POKEMON_CASES = sorted(_dex_data()[1].items(), key=lambda pair: pair[0])


def _callback_refs(raw):
    for key, value in (raw or {}).items():
        if not isinstance(value, str) or "." not in value:
            continue
        if key.startswith("on") or key.endswith("Callback"):
            yield key, value


@pytest.mark.parametrize(
    ("item_name", "item"),
    ITEM_CASES,
    ids=[name for name, _item in ITEM_CASES],
)
def test_all_item_callback_references_resolve(item_name, item):
    for callback_key, callback_ref in _callback_refs(getattr(item, "raw", {}) or {}):
        assert callable(
            resolve_callback_from_modules(callback_ref, "pokemon.dex.functions.items_funcs")
        ), f"{item_name}.{callback_key} -> {callback_ref} did not resolve"


@pytest.mark.parametrize(
    ("item_name", "item"),
    ITEM_CASES,
    ids=[name for name, _item in ITEM_CASES],
)
def test_all_held_items_can_be_assigned_in_minimal_battle(item_name, item):
    battle, user, _target = build_outcome_battle()

    assert battle.set_item(user, copy.deepcopy(item)) is True, item_name


@pytest.mark.parametrize(
    ("species_name", "_entry"),
    POKEMON_CASES,
    ids=[name for name, _entry in POKEMON_CASES],
)
def test_all_pokemon_can_build_outcome_specs(species_name, _entry):
    spec = pokemon_spec_from_dex(species_name)
    battle, user, _target = build_outcome_battle(user=spec)

    assert str(user.species) == spec.name
    assert user.types == list(spec.types)
