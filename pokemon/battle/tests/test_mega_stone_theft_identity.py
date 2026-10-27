"""Native Mega Stone protection through genuine removal moves and forms."""

from types import SimpleNamespace

import pytest

from pokemon.battle.effect_context import EffectContext
from pokemon.battle.mega_pairs import MEGA_PAIRS
from pokemon.dex import ITEMDEX, POKEDEX
from pokemon.dex.entities import Stats
from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats
from pokemon.names import resolve_dex_entry

from .test_diagnosed_item_effects import attack
from .test_plate_theft_identity import held, pair


STONES = tuple(
    (resolve_dex_entry(ITEMDEX, key).raw["name"], native, form)
    for key, (native, form) in sorted(MEGA_PAIRS.items())
)
REMOVAL_MOVES = ("Thief", "Knock Off", "Trick", "Switcheroo")


def stone_pair(item, native, *, eligible=True, source="Mew"):
    """Use calculated native stats and real dex abilities, retaining nicknames."""
    species = native if eligible else "Mew"
    ability = resolve_dex_entry(POKEDEX, species).raw["abilities"]["0"]
    battle, holder, thief = pair(
        item, holder=species, source=source,
        nickname="Buddy" if eligible else native, ability=ability,
    )
    data = SimpleNamespace(species=species, level=50, nature="Bold",
                           ivs=[31] * 6, evs=[252, 0, 252, 0, 0, 0])
    holder.ivs, holder.evs, holder.nature = data.ivs, data.evs, data.nature
    stats = get_stats(data)
    holder.hp = holder.max_hp = get_max_hp(data)
    holder.base_stats = Stats(**stats)
    holder.stats = {short: stats[long] for short, long in (
        ("hp", "hp"), ("atk", "attack"), ("def", "defense"),
        ("spa", "special_attack"), ("spd", "special_defense"), ("spe", "speed"),
    )}
    thief.ability = resolve_dex_entry(POKEDEX, source).raw["abilities"]["0"]
    return battle, holder, thief


def test_exact_standard_mega_inventory_excludes_cap():
    """The repair must cover all 47 accepted stones and no CAP definition."""
    canonical = {
        item.raw["name"] for item in ITEMDEX.values()
        if item.raw.get("megaStone") and item.raw.get("isNonstandard") != "CAP"
    }
    assert len(STONES) == len(canonical) == 47
    assert {item for item, _, _ in STONES} == canonical
    assert "Crucibellite" not in canonical


@pytest.mark.parametrize("item,native,form", STONES, ids=[row[0] for row in STONES])
@pytest.mark.parametrize("eligible", (False, True), ids=("foreign-nickname", "renamed-native"))
@pytest.mark.parametrize("move", REMOVAL_MOVES)
def test_all_stones_use_native_holder_for_actual_removal_moves(item, native, form, eligible, move):
    """Real damage/removal/swap cannot derive protection from a display name."""
    battle, holder, thief = stone_pair(
        item, native, eligible=eligible, source="Hypno" if move == "Switcheroo" else "Mew",
    )
    swap = move in {"Trick", "Switcheroo"}
    if swap:
        assert battle.set_item(thief, "Shed Shell")
    identity = (str(holder.species), str(holder.base_species), holder.name)
    damage, _ = attack(battle, thief, holder, move)
    if move in {"Thief", "Knock Off"}:
        assert 0 < damage < holder.max_hp
    stone, shell = EffectContext.key(item), "shedshell" if swap else ""
    expected = (stone, shell) if eligible else ("", "") if move == "Knock Off" else (shell, stone)
    assert (held(holder), held(thief)) == expected
    assert (str(holder.species), str(holder.base_species), holder.name) == identity
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,native,form", STONES, ids=[row[0] for row in STONES])
@pytest.mark.parametrize("native_source", (False, True))
def test_compatible_or_named_source_cannot_protect_a_foreign_holder(item, native, form, native_source):
    """TakeItem's holder is distinct from the thief; this is not a learnset test."""
    battle, holder, thief = stone_pair(
        item, native, eligible=False, source=native if native_source else "Mew",
    )
    holder.name = "Friend"
    thief.name = "Buddy" if native_source else native
    assert battle.take_item(holder, source=thief) is not None
    assert not held(holder)
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,native,form", STONES, ids=[row[0] for row in STONES])
def test_actual_mega_form_retains_native_protection_and_calculated_state(item, native, form):
    """A real form change preserves native identity independently of form name."""
    battle, holder, thief = stone_pair(item, native)
    assert holder.formeChange(form, battle=battle)
    holder.name = "Buddy"
    before = (str(holder.species), str(holder.base_species), holder.max_hp,
              dict(vars(holder.base_stats)), list(holder.types), holder.ability)
    assert battle.take_item(holder, source=thief) is None
    assert held(holder) == EffectContext.key(item)
    assert (str(holder.species), str(holder.base_species), holder.max_hp,
            dict(vars(holder.base_stats)), list(holder.types), holder.ability) == before
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("suppression", ("magicroom", "embargo", "klutz"))
@pytest.mark.parametrize("eligible", (False, True))
@pytest.mark.parametrize("move", REMOVAL_MOVES)
def test_suppression_keeps_physical_native_protection_without_effects(suppression, eligible, move):
    """Suppressed held effects cannot erase or invent physical theft protection."""
    battle, holder, thief = stone_pair("Blastoisinite", "Blastoise", eligible=eligible)
    if suppression == "magicroom":
        battle.add_pseudo_weather("magicroom", source=thief)
    elif suppression == "embargo":
        battle.apply_volatile_status(holder, "embargo", source=thief)
    else:
        holder.ability = "Klutz"  # Suppression adapter, not a native ability claim.
    assert EffectContext.item(holder) is None
    attack(battle, thief, holder, move)
    assert bool(held(holder)) is eligible
    assert bool(held(thief)) is (not eligible and move != "Knock Off")
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("native_holder", (False, True))
def test_real_transform_follows_original_identity_in_both_directions(native_holder):
    """Actual copied appearance cannot grant or erase native stone protection."""
    battle, holder, thief = stone_pair(
        "Blastoisinite", "Blastoise", eligible=native_holder,
        source="Mew" if native_holder else "Blastoise",
    )
    # Native Blastoise's Transform is a mechanics adapter, not a learnset claim.
    attack(battle, holder, thief, "Transform")
    assert holder.transformed
    holder.name = "Buddy" if native_holder else "Blastoise"
    attack(battle, thief, holder, "Thief")
    assert bool(held(holder)) is native_holder
    assert bool(held(thief)) is not native_holder
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("move", REMOVAL_MOVES)
def test_sticky_hold_and_occupied_thief_remain_independent_controls(move):
    """Generic anti-theft still protects a non-native stone holder."""
    battle, holder, thief = pair(
        "Blastoisinite", holder="Gastrodon", nickname="Blastoise", ability="Sticky Hold",
    )
    if move in {"Trick", "Switcheroo"}:
        battle.set_item(thief, "Shed Shell")
    attack(battle, thief, holder, move)
    assert held(holder) == "blastoisinite"
    assert held(thief) == ("shedshell" if move in {"Trick", "Switcheroo"} else "")
    battle, holder, thief = stone_pair("Blastoisinite", "Blastoise", eligible=False)
    battle.set_item(thief, "Shed Shell")
    attack(battle, thief, holder, "Thief")
    assert (held(holder), held(thief)) == ("blastoisinite", "shedshell")


@pytest.mark.parametrize("identity", ({}, {"base_species": "Blastoise-Fake"},
                                     {"base_species": "", "species": "Blastoise"}))
def test_unknown_native_identity_never_uses_display_or_foreign_source(identity):
    """Malformed adapters receive no name-based protection from a real thief."""
    item = resolve_dex_entry(ITEMDEX, "Blastoisinite")
    holder = SimpleNamespace(name="Blastoise", **identity)
    source = SimpleNamespace(base_species="Blastoise", species="Blastoise", name="Blastoise")
    assert item.call("onTakeItem", item=item, pokemon=holder, source=source) is True
