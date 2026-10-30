"""Effective minted stats with unchanged genetics, caches and serialized form state."""

from copy import deepcopy
from math import floor
from types import SimpleNamespace

import pytest

from pokemon.nature_training import NatureTraining, NatureTrainingError


def learner(**changes):
    """Use real species data and project stat helpers, with explicit genetic prerequisites."""
    return SimpleNamespace(
        **{
            **dict(
                species="Mew",
                level=50,
                nature="Hardy",
                trained_stat_nature=None,
                ivs=[8] * 6,
                evs=[0] * 6,
                flags=[],
            ),
            **changes,
        }
    )


@pytest.mark.parametrize("nature", NatureTraining.mint_names)
def test_every_preference_reaches_exact_non_hp_modifiers_and_preserves_genetics(nature):
    """All21 preferences reach the stat consumer with +10/-10 percent flooring."""
    from pokemon.helpers.pokemon_helpers import get_stats
    from pokemon.data.generation import NATURES

    plain = learner()
    baseline = get_stats(plain)
    minted = learner(trained_stat_nature=nature)
    saved = deepcopy(vars(minted))
    actual = get_stats(minted)
    increase, decrease = NATURES[nature]
    for stat, value in baseline.items():
        expected = floor(value * (1.1 if stat == increase else 0.9 if stat == decrease else 1))
        assert actual[stat] == expected
    assert vars(minted) == saved and minted.nature == "Hardy"


def test_old_explicit_stat_cache_cannot_hide_new_training_or_malformed_state():
    """Cached genetic stats cannot override a paid preference or conceal corrupt training."""
    from pokemon.helpers.pokemon_helpers import get_stats

    mon = learner()
    mon._cached_stats = get_stats(mon)
    old = dict(mon._cached_stats)
    mon.trained_stat_nature = "Adamant"
    current = get_stats(mon)
    assert current["attack"] > old["attack"] and current["special_attack"] < old["special_attack"]
    mon.trained_stat_nature = "unknown"
    with pytest.raises(NatureTrainingError):
        get_stats(mon)


def test_hyper_training_remains_an_independent_genetic_iv_overlay():
    """Mint modifiers compose with real Hyper Training without rewriting either field."""
    from pokemon.helpers.pokemon_helpers import get_stats

    mon = learner(trained_stat_nature="Adamant", flags=["hypertrained:attack"])
    expected = learner(nature="Adamant", ivs=[8, 31, 8, 8, 8, 8])
    assert get_stats(mon) == get_stats(expected)
    assert mon.ivs == [8] * 6 and mon.nature == "Hardy"


def test_constructor_checkpoint_and_form_calculation_preserve_both_values():
    """A real battle object restores the same trained stats and genetic Nature."""
    from pokemon.battle.battledata import Pokemon
    from pokemon.battle.mega_evolution import MegaEvolution
    from pokemon.helpers.pokemon_helpers import get_stats

    pokemon = Pokemon(
        "Mew", level=50, nature="Hardy", trained_stat_nature="Modest", ivs=[8] * 6, evs=[0] * 6
    )
    expected = get_stats(learner(trained_stat_nature="Modest"))
    assert {key: getattr(pokemon.base_stats, key) for key in expected} == expected
    restored = Pokemon.from_dict(pokemon.to_dict())
    assert restored.nature == "Hardy" and restored.trained_stat_nature == "Modest"
    assert {key: getattr(restored.base_stats, key) for key in expected} == expected
    assert MegaEvolution.species_stats(restored) == expected
    assert restored.formeChange("Mewtwo")
    assert restored.nature == "Hardy" and restored.trained_stat_nature == "Modest"
    assert (
        get_stats(restored)["special_attack"]
        > get_stats(learner(species="Mewtwo"))["special_attack"]
    )


@pytest.mark.parametrize("value", [False, 1, [], "unknown", "Hardy", "adamant"])
def test_serialized_training_rejects_before_any_random_stat_or_builder_fallback(value):
    """Malformed new state cannot be hidden by constructor or raw-data compatibility."""
    from pokemon.battle.battledata import Pokemon
    from utils.pokemon_utils import make_pokemon_from_dict

    state = {"name": "Mew", "nature": "Hardy", "trained_stat_nature": value}
    with pytest.raises(NatureTrainingError):
        Pokemon.from_dict(state)
    with pytest.raises(NatureTrainingError):
        make_pokemon_from_dict(state)


def test_legacy_untrained_checkpoint_keeps_actual_genetic_nature():
    """Absent new state in an old standalone snapshot uses its genetic modifier."""
    from pokemon.battle.battledata import Pokemon

    pokemon = Pokemon.from_dict({"name": "Mew", "level": 50, "nature": "Jolly"})
    assert pokemon.nature == "Jolly" and pokemon.trained_stat_nature is None
    assert pokemon.base_stats.speed > pokemon.base_stats.special_attack


def test_encounter_checkpoint_cannot_invent_a_minted_training_overlay():
    """Wild/NPC genetics start untrained; the bag route requires an owned source."""
    from pokemon.battle.battledata import Pokemon

    with pytest.raises(ValueError, match="Encounter"):
        Pokemon(
            "Mew",
            nature="Hardy",
            trained_stat_nature="Adamant",
            model_id="encounter:12345678-1234-1234-1234-123456789abc",
        )


@pytest.mark.parametrize(
    "item,disliked",
    [
        ("Figy Berry", "Modest"),
        ("Wiki Berry", "Adamant"),
        ("Mago Berry", "Brave"),
        ("Aguav Berry", "Naughty"),
        ("Iapapa Berry", "Lonely"),
    ],
)
@pytest.mark.parametrize("genetic_dislike", [False, True])
def test_actual_flavor_berry_callback_keeps_genetic_preferences(item, disliked, genetic_dislike):
    """A contrary mint preference can neither add nor suppress genetic confusion."""
    from pokemon.battle.tests.test_diagnosed_item_effects import native_battle

    battle, holder, _ = native_battle(item=item, hp_fraction=0.2, ability="No Ability")
    holder.nature = disliked if genetic_dislike else "Hardy"
    holder.trained_stat_nature = "Serious" if genetic_dislike else disliked
    before = holder.hp
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert holder.hp == min(holder.max_hp, before + holder.max_hp // 3)
    assert holder.item is None
    assert ("confusion" in holder.volatiles) is genetic_dislike
