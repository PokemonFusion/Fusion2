"""Real damage and native identity for the seven existing legendary boosters."""

import random
from types import SimpleNamespace

import pytest

from .test_diagnosed_item_effects import attack, native_battle


PROFILES = (
    ("Adamant Orb", "Dialga", "Dialga", "Flash Cannon"),
    ("Adamant Crystal", "Dialga", "Dialga-Origin", "Flash Cannon"),
    ("Lustrous Orb", "Palkia", "Palkia", "Water Pulse"),
    ("Lustrous Globe", "Palkia", "Palkia-Origin", "Water Pulse"),
    ("Griseous Orb", "Giratina", "Giratina", "Shadow Ball"),
    ("Griseous Core", "Giratina", "Giratina-Origin", "Shadow Ball"),
    ("Soul Dew", "Latias", "Latias", "Psychic"),
)


def measure(item, species, move, *, nickname=None, suppression=None, copied=None):
    """Execute a genuine move and read its item's exact effective power rule."""
    from pokemon.battle.effect_context import EffectContext
    from pokemon.dex import MOVEDEX
    from pokemon.names import resolve_dex_entry

    battle, holder, foe = native_battle(species, item=item, foe=copied or "Wailord")
    if copied:
        attack(battle, holder, foe, "Transform")
        assert holder.transformed and str(holder.base_species) == species
    if nickname:
        holder.name = nickname
    if suppression == "magicroom":
        battle.add_pseudo_weather("magicroom", source=foe)
    elif suppression == "embargo":
        battle.apply_volatile_status(holder, "embargo", source=foe)
    elif suppression == "klutz":
        holder.ability = "Klutz"
    entry = resolve_dex_entry(MOVEDEX, move)
    active = EffectContext.item(holder)
    power = (
        active.call(
            "onBasePower",
            entry.power,
            user=holder,
            target=foe,
            move=SimpleNamespace(type=entry.type),
        )
        if active
        else entry.power
    )
    battle.rng = random.Random(854)
    damage, _ = attack(battle, holder, foe, move)
    assert damage > 0
    assert not getattr(battle, "_callback_failures", [])
    return damage, power, entry.power, str(holder.species)


@pytest.mark.parametrize("item,native,current,second", PROFILES)
@pytest.mark.parametrize("renamed", (False, True))
@pytest.mark.parametrize("alternate", (False, True))
def test_native_matching_types_retain_power_and_real_damage(
    item, native, current, second, renamed, alternate
):
    """Paired identical native forms distinguish the item from form-stat changes."""
    move = second if alternate else "Dragon Pulse"
    options = {"nickname": "Buddy" if renamed else None}
    baseline = measure("", current, move, **options)
    held = measure(item, current, move, **options)
    assert held[1] == int(baseline[2] * 1.2)
    assert held[0] > baseline[0]


@pytest.mark.parametrize("item,native,current,second", PROFILES)
@pytest.mark.parametrize("suffix", ("", "-Imposter"))
@pytest.mark.parametrize("alternate", (False, True))
def test_foreign_exact_or_prefix_nickname_cannot_boost_either_type(
    item, native, current, second, suffix, alternate
):
    """A foreign name cannot gain power, damage or the native Origin form."""
    move = second if alternate else "Dragon Pulse"
    options = {"nickname": native + suffix}
    baseline = measure("", "Mew", move, **options)
    held = measure(item, "Mew", move, **options)
    assert held == baseline
    assert held[3] == "Mew"


@pytest.mark.parametrize("item,native,current,second", PROFILES)
def test_nonmatching_native_move_has_no_power_or_damage_bonus(item, native, current, second):
    """Swift stays unboosted even on the correct renamed native form."""
    baseline = measure("", current, "Swift", nickname="Buddy")
    assert measure(item, current, "Swift", nickname="Buddy") == baseline


@pytest.mark.parametrize("item,native,current,second", PROFILES)
@pytest.mark.parametrize("suppression", ("magicroom", "embargo", "klutz"))
@pytest.mark.parametrize("alternate", (False, True))
def test_suppression_blocks_both_native_type_bonuses(
    item, native, current, second, suppression, alternate
):
    """The shared identity query cannot bypass effective held-item suppression."""
    move = second if alternate else "Dragon Pulse"
    options = {"nickname": "Buddy", "suppression": suppression}
    baseline = measure("", current, move, **options)
    assert measure(item, current, move, **options) == baseline


@pytest.mark.parametrize("item,native,current,second", PROFILES)
def test_genuine_native_transform_retains_the_base_species_bonus(item, native, current, second):
    """The seven power rules follow native identity through actual Transform."""
    # Transform is assigned for this copy-policy fixture, not a learnset claim.
    baseline = measure("", current, "Dragon Pulse", copied="Mew")
    held = measure(item, current, "Dragon Pulse", copied="Mew", nickname="Buddy")
    assert held[1] == int(baseline[2] * 1.2)
    assert held[0] > baseline[0]
    assert held[3] == "Mew"


@pytest.mark.parametrize("item,native,current,second", PROFILES)
def test_foreign_transform_into_a_native_appearance_never_gains_power(
    item, native, current, second
):
    """A real Mew Transform cannot counterfeit the legendary native identity."""
    baseline = measure("", "Mew", "Dragon Pulse", copied=current)
    assert measure(item, "Mew", "Dragon Pulse", copied=current) == baseline


@pytest.mark.parametrize(
    "item,species",
    (
        ("Adamant Orb", "Dialga-Origin"),
        ("Lustrous Orb", "Palkia-Origin"),
        ("Griseous Orb", "Giratina-Origin"),
        ("Soul Dew", "Latios"),
        ("Soul Dew", "Latias-Mega"),
        ("Soul Dew", "Latios-Mega"),
    ),
)
def test_canonical_related_forms_retain_the_native_type_bonus(item, species):
    """Known forms follow the reference base species without enabling new forms."""
    baseline = measure("", species, "Dragon Pulse", nickname="Buddy")
    held = measure(item, species, "Dragon Pulse", nickname="Buddy")
    assert held[1] == int(baseline[2] * 1.2)
    assert held[0] > baseline[0]
