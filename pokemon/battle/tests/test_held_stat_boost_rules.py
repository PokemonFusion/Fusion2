"""Native held-stat triggers must affect real calculations and checkpoints."""

import json
import random
from types import SimpleNamespace

import pytest

from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats

from .test_diagnosed_item_effects import attack, native_battle
from .test_reactive_item_consumption import name


PINCH = {"Liechi Berry": {"atk": 1}, "Ganlon Berry": {"def": 1},
         "Salac Berry": {"spe": 1}, "Petaya Berry": {"spa": 1},
         "Apicot Berry": {"spd": 1}, "Starf Berry": {"atk": 2}}
REACTIVE = {"Absorb Bulb": ("Water Gun", {"spa": 1}),
            "Cell Battery": ("Thunder Shock", {"atk": 1}),
            "Luminous Moss": ("Water Gun", {"spd": 1}),
            "Snowball": ("Ice Shard", {"atk": 1}),
            "Kee Berry": ("Tackle", {"def": 1}),
            "Maranga Berry": ("Water Gun", {"spd": 1}),
            "Weakness Policy": ("Payback", {"atk": 2, "spa": 2}),
            "Throat Spray": ("Screech", {"spa": 1})}
SEEDS = {"Electric Seed": ("Electric Terrain", {"def": 1}),
         "Grassy Seed": ("Grassy Terrain", {"def": 1}),
         "Misty Seed": ("Misty Terrain", {"spd": 1}),
         "Psychic Seed": ("Psychic Terrain", {"spd": 1})}
ITEMS = tuple(PINCH) + tuple(REACTIVE) + tuple(SEEDS)
NATIVES = (("Mew", "Synchronize", 1), ("Shuckle", "Contrary", -1),
           ("Bibarel", "Simple", 2))


def scenario(item, species="Mew", ability="Synchronize"):
    """Equip a native holder against a durable, low-level real-stat source."""
    battle, holder, foe = native_battle(species, item, "Mew", ability=ability)
    data = SimpleNamespace(species="Mew", level=5, ivs=[0] * 6, evs=[0] * 6, nature="Hardy")
    foe.level = 5
    foe.base_stats = type(holder.base_stats)(**get_stats(data))
    foe.stats = get_stats(data)
    foe.hp = foe.max_hp = get_max_hp(data)
    battle.rng = random.Random(0)
    return battle, holder, foe


def trigger(battle, holder, foe, item):
    """Use genuine hits, sound, terrain or the normal low-HP update."""
    if item in PINCH:
        holder.hp = holder.max_hp // 4
        battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    elif item in SEEDS:
        attack(battle, foe, foe, SEEDS[item][0])
    elif item == "Throat Spray":
        attack(battle, holder, foe, REACTIVE[item][0])
    else:
        attack(battle, foe, holder, ("Water Gun" if holder.species == "Shuckle" else
                                    "Magical Leaf" if holder.species == "Bibarel" else "Payback")
               if item == "Weakness Policy" else REACTIVE[item][0])


@pytest.mark.parametrize("item", ITEMS)
@pytest.mark.parametrize("species,ability,multiplier", NATIVES)
@pytest.mark.parametrize("prior", (-6, -2, 0, 2, 6))
def test_exact_stat_deltas_preserve_existing_stages_and_real_stats(item, species, ability, multiplier, prior):
    """Every listed item respects normalization, both caps and native abilities."""
    from pokemon.battle.utils import get_modified_stat
    from pokemon.utils.boosts import STAT_KEY_MAP

    battle, holder, foe = scenario(item, species, ability)
    effects = PINCH.get(item) or (REACTIVE.get(item) or SEEDS[item])[1]
    if item == "Starf Berry":
        holder.boosts.update({STAT_KEY_MAP[key]: 6 for key in ("def", "spa", "spd", "spe")})
    for key in effects:
        holder.boosts[STAT_KEY_MAP[key]] = prior
    before = {key: get_modified_stat(holder, STAT_KEY_MAP[key]) for key in effects}
    trigger(battle, holder, foe, item)
    assert holder.hp > 0 and foe.hp > 0
    for key, amount in effects.items():
        full = STAT_KEY_MAP[key]
        expected = min(6, max(-6, prior + amount * multiplier))
        if item == "Starf Berry" and prior == 6:
            expected = 6  # No reference-eligible stat remains, but eating still occurs.
        assert holder.boosts[full] == expected
        assert key not in holder.boosts
        after = get_modified_stat(holder, full)
        assert (after > before[key]) == (expected > prior)
        assert (after < before[key]) == (expected < prior)
    assert name(holder.item) == "" and name(holder.last_used_item) == item
    assert [name(value) for value in holder.side.used_items] == [item]
    assert not getattr(battle, "_callback_failures", [])


def test_liechi_never_overwrites_three_earned_swords_dances():
    """An actual +6 Attack remains useful after the cap-triggered berry use."""
    from pokemon.battle.utils import get_modified_stat

    battle, holder, foe = scenario("Liechi Berry")
    for _ in range(3):
        attack(battle, holder, holder, "Swords Dance")
    assert holder.boosts["attack"] == 6
    before = get_modified_stat(holder, "attack")
    trigger(battle, holder, foe, "Liechi Berry")
    assert holder.boosts["attack"] == 6
    assert get_modified_stat(holder, "attack") == before
    assert "atk" not in holder.boosts and name(holder.item) == ""


@pytest.mark.parametrize("item", PINCH)
@pytest.mark.parametrize("species,ability,consumed", (("Mew", "Synchronize", False),
                                                     ("Snorlax", "Gluttony", True)))
def test_pinch_half_hp_requires_effective_native_gluttony(item, species, ability, consumed):
    """Half HP is permitted only by active Gluttony, retaining one use."""
    battle, holder, foe = scenario(item, species, ability)
    holder.hp = holder.max_hp // 2
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert bool(name(holder.item)) is not consumed
    if consumed:
        assert name(holder.last_used_item) == item


@pytest.mark.parametrize("item", ITEMS)
def test_magic_room_preserves_item_and_stages(item):
    """Suppressed holders cannot consume or apply a qualified stat item."""
    battle, holder, foe = scenario(item)
    attack(battle, foe, foe, "Magic Room")
    before = dict(holder.boosts)
    trigger(battle, holder, foe, item)
    assert name(holder.item) == item and not holder.last_used_item
    assert {k: v for k, v in holder.boosts.items() if v} == {k: v for k, v in before.items() if v}
    assert holder.side.used_items == []


@pytest.mark.parametrize("item", SEEDS)
def test_seed_entry_matching_terrain_once_then_recycle_in_wrong_terrain(item):
    """Entry and later terrain changes each require the actual matching field."""
    from pokemon.dex import ITEMDEX
    from pokemon.names import resolve_dex_entry

    battle, holder, foe = scenario("")
    attack(battle, foe, foe, SEEDS[item][0])
    assert battle.set_item(holder, resolve_dex_entry(ITEMDEX, item))
    assert not holder.item and name(holder.last_used_item) == item
    before = dict(holder.boosts)
    battle.runEvent("TerrainChange", holder)
    assert holder.boosts == before and len(holder.side.used_items) == 1
    wrong = "Misty Terrain" if item != "Misty Seed" else "Grassy Terrain"
    attack(battle, foe, foe, wrong)
    attack(battle, holder, holder, "Recycle")
    assert name(holder.item) == item and holder.boosts == before


def test_starf_random_state_round_trip_replays_future_choice_without_global_draws():
    """Pending choice and committed choice survive JSON rebuilds identically."""
    from pokemon.battle.battledata import Pokemon
    from pokemon.battle.item_boosts import ItemRandomState

    battle, holder, foe = scenario("Starf Berry")
    saved = json.loads(json.dumps(ItemRandomState.freeze(battle)))
    before = random.getstate()
    trigger(battle, holder, foe, "Starf Berry")
    chosen = dict(holder.boosts)
    rebuilt, copy, other = scenario("Starf Berry")
    ItemRandomState.restore(rebuilt, saved)
    trigger(rebuilt, copy, other, "Starf Berry")
    assert copy.boosts == chosen and random.getstate() == before
    restored = Pokemon.from_dict(json.loads(json.dumps(copy.to_dict())))
    assert restored.boosts == chosen and not restored.item
    assert name(restored.last_used_item) == "Starf Berry"


@pytest.mark.parametrize("payload", ({}, [], [True, [], None], [3, [0] * 625, "bad"],
                                   [3, [0] * 624 + [626], None]))
def test_corrupt_starf_random_state_refuses_without_mutation(payload):
    """Malformed explicit histories never reset randomness or partially load."""
    from pokemon.battle.item_boosts import ItemRandomState

    battle, _, _ = scenario("Starf Berry")
    before = battle.rng.getstate()
    with pytest.raises(ValueError, match="random state"):
        ItemRandomState.restore(battle, payload)
    assert battle.rng.getstate() == before
