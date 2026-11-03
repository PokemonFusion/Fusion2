"""Effective IV overlays must preserve genetics through stats and snapshots."""

from types import SimpleNamespace

import pytest

from pokemon.hyper_training import HyperTraining


@pytest.mark.parametrize("stat", HyperTraining.stats)
def test_overlay_copies_genetics_in_array_and_mapping_representations(stat):
    """A trained stat alone uses 31 without mutating either genetic container."""
    genetic = [1, 2, 3, 4, 5, 6]
    owner = SimpleNamespace(flags=["other", "hypertrained:" + stat])
    result = HyperTraining.effective(genetic, owner)
    expected = genetic.copy()
    expected[HyperTraining.stats.index(stat)] = 31
    assert result == expected
    assert genetic == [1, 2, 3, 4, 5, 6]
    mapping = dict(zip(("hp", "atk", "def", "spa", "spd", "spe"), genetic))
    effective = HyperTraining.effective(mapping, owner)
    assert list(effective.values()) == expected
    assert list(mapping.values()) == genetic


def test_owned_flags_take_precedence_over_unsaved_runtime_overlay():
    """Runtime attributes cannot replace the persisted owned training contract."""
    owner = SimpleNamespace(flags=["hypertrained:attack"], hyper_training=["speed"])
    assert HyperTraining.trained(owner) == ["attack"]


def test_runtime_stats_roundtrip_keep_genetic_ivs_and_trained_values():
    """A standalone serialized Pokemon retains overlay and all six real stats."""
    from pokemon.battle.battledata import Pokemon
    from pokemon.helpers.pokemon_helpers import get_stats

    genetic = [0, 1, 2, 3, 4, 5]
    pokemon = Pokemon("Mew", level=50, ivs=genetic.copy(), hyper_training=list(HyperTraining.stats))
    expected = get_stats(SimpleNamespace(species="Mew", level=50, ivs=[31] * 6, evs=[0] * 6, nature="Hardy"))
    assert get_stats(pokemon) == expected
    assert vars(pokemon.base_stats) == expected
    payload = pokemon.to_dict()
    assert payload["ivs"] == genetic
    assert payload["hyper_training"] == list(HyperTraining.stats)
    restored = Pokemon.from_dict(payload)
    assert restored.ivs == genetic
    assert vars(restored.base_stats) == expected
    assert restored.to_dict()["hyper_training"] == list(HyperTraining.stats)


def test_legacy_and_invalid_standalone_overlay_snapshots_do_not_invent_training():
    """Absent or malformed overlay data is backward-compatible and cannot boost."""
    from pokemon.battle.battledata import Pokemon

    for overlay in (None, "attack", ["not_a_stat"], {"hp": True}):
        data = {"name": "Mew", "species": "Mew", "level": 50, "ivs": [0] * 6}
        if overlay is not None:
            data["hyper_training"] = overlay
        restored = Pokemon.from_dict(data)
        assert restored.hyper_training == []
        assert restored.ivs == [0] * 6


def test_native_form_recalculation_keeps_training_and_genetics():
    """Normal/native form helpers must not lose the overlay during recalculation."""
    from pokemon.battle.battledata import Pokemon
    from pokemon.battle.native_forms import NativeBattleForm
    from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats

    pokemon = Pokemon("Darmanitan", level=50, ivs=[0] * 6,
                      hyper_training=list(HyperTraining.stats), ability="Zen Mode")
    pokemon.max_hp = get_max_hp(pokemon)
    pokemon.hp = pokemon.max_hp - 9
    assert pokemon.formeChange("Darmanitan-Zen", preserve_ability=True)
    expected = get_stats(SimpleNamespace(species="Darmanitan-Zen", level=50,
                                        ivs=[31] * 6, evs=[0] * 6, nature="Hardy"))
    assert vars(pokemon.base_stats) == expected
    assert pokemon.ivs == [0] * 6
    assert pokemon.max_hp - pokemon.hp == 9
    turtle = Pokemon("Terapagos", level=50, ivs=[0] * 6,
                     hyper_training=list(HyperTraining.stats), ability="Tera Shift")
    turtle.max_hp = get_max_hp(turtle)
    turtle.hp = turtle.max_hp - 9
    assert NativeBattleForm.tera_shift(turtle)
    expected = get_stats(SimpleNamespace(species="Terapagos-Terastal", level=50,
                                        ivs=[31] * 6, evs=[0] * 6, nature="Hardy"))
    assert vars(turtle.base_stats) == expected
    assert turtle.max_hp - turtle.hp == 9
    assert NativeBattleForm.restore(turtle)
    assert turtle.ivs == [0] * 6
    assert turtle.max_hp - turtle.hp == 9


def test_scaled_battle_level_retains_previously_earned_training():
    """Temporary battle scaling below 50 does not remove permanent training."""
    from pokemon.battle.battledata import Pokemon
    from pokemon.helpers.pokemon_helpers import get_stats

    pokemon = Pokemon("Mew", level=5, ivs=[0] * 6, hyper_training=list(HyperTraining.stats))
    expected = get_stats(SimpleNamespace(species="Mew", level=5, ivs=[31] * 6, evs=[0] * 6, nature="Hardy"))
    assert vars(pokemon.base_stats) == expected
    assert pokemon.ivs == [0] * 6
