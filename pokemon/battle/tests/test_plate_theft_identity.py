"""Native Plate removal rules through real damage, transfer and item events."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from pokemon.battle.effect_context import EffectContext
from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats

from .test_diagnosed_item_effects import attack, native_battle


PLATES = (
    ("Draco Plate", "Dragon Pulse"), ("Dread Plate", "Dark Pulse"),
    ("Earth Plate", "Earth Power"), ("Fist Plate", "Aura Sphere"),
    ("Flame Plate", "Flamethrower"), ("Icicle Plate", "Ice Beam"),
    ("Insect Plate", "Bug Buzz"), ("Iron Plate", "Flash Cannon"),
    ("Meadow Plate", "Energy Ball"), ("Mind Plate", "Psychic"),
    ("Pixie Plate", "Dazzling Gleam"), ("Sky Plate", "Air Slash"),
    ("Splash Plate", "Surf"), ("Spooky Plate", "Shadow Ball"),
    ("Stone Plate", "Power Gem"), ("Toxic Plate", "Sludge Bomb"),
    ("Zap Plate", "Thunderbolt"),
)


def pair(item, *, holder="Mew", source="Mew", nickname="Buddy", ability="Synchronize"):
    """Use native stats at level 50 on both sides to avoid lethal theft fixtures."""
    battle, target, thief = native_battle(holder, item=item, foe=source, ability=ability)
    data = SimpleNamespace(species=source, level=50, ivs=[0] * 6, evs=[0] * 6, nature="Hardy")
    stats = get_stats(data)
    thief.level = 50
    thief.hp = thief.max_hp = get_max_hp(data)
    for short, long in (("atk", "attack"), ("def", "defense"), ("spa", "special_attack"),
                        ("spd", "special_defense"), ("spe", "speed")):
        thief.stats[short] = stats[long]
        setattr(thief.base_stats, long, stats[long])
    thief.ability = "Multitype" if source.startswith("Arceus") else "Synchronize"
    target.name = nickname
    thief.name = "Friend"
    return battle, target, thief


def held(mon):
    """Read physical holding independently of active item suppression."""
    return EffectContext.key(getattr(mon, "item", None))


@pytest.mark.parametrize("item,move", PLATES)
@pytest.mark.parametrize("nickname", ("Mew", "Arceus", "Arceus-Imposter"))
def test_foreign_names_do_not_block_actual_thief(item, move, nickname):
    """Identical foreign holders lose exactly one Plate regardless of nickname."""
    battle, target, thief = pair(item, nickname=nickname)
    damage, _ = attack(battle, thief, target, "Thief")
    assert 0 < damage < target.max_hp
    assert not held(target) and held(thief) == EffectContext.key(item)
    assert str(target.species) == "Mew"
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,move", PLATES)
@pytest.mark.parametrize("nickname", ("Arceus", "Arceus-Imposter"))
def test_foreign_source_name_cannot_block_actual_thief(item, move, nickname):
    """The source role uses the same native query as the Plate's holder."""
    battle, target, thief = pair(item)
    thief.name = nickname
    damage, _ = attack(battle, thief, target, "Thief")
    assert 0 < damage < target.max_hp
    assert not held(target) and held(thief) == EffectContext.key(item)


@pytest.mark.parametrize("item,move", PLATES)
@pytest.mark.parametrize("role", ("holder", "source"))
@pytest.mark.parametrize("nickname", ("Arceus", "Buddy"))
def test_native_holder_or_source_blocks_actual_thief(item, move, role, nickname):
    """Either canonical native Arceus participant protects the Plate."""
    battle, target, thief = pair(
        item, holder="Arceus" if role == "holder" else "Mew",
        source="Arceus" if role == "source" else "Mew", nickname=nickname,
        ability="Multitype" if role == "holder" else "Synchronize",
    )
    thief.name = nickname
    damage, _ = attack(battle, thief, target, "Thief")
    assert 0 < damage < target.max_hp
    assert held(target) == EffectContext.key(item) and not held(thief)
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,move", PLATES)
def test_non_arceus_keeps_generic_matching_type_boost(item, move):
    """All seventeen generic power callbacks remain available to native Mew."""
    from .test_legendary_item_identity import measure

    baseline = measure("", "Mew", move, nickname="Arceus")
    boosted = measure(item, "Mew", move, nickname="Arceus")
    assert boosted[1] == int(baseline[2] * 1.2)
    assert boosted[0] > baseline[0]
    assert boosted[3] == "Mew"


@pytest.mark.parametrize("suppression", ("magicroom", "embargo", "klutz"))
@pytest.mark.parametrize("native", (False, True))
@pytest.mark.parametrize("move", ("Thief", "Knock Off", "Trick", "Switcheroo"))
def test_suppression_never_invents_or_removes_native_protection(suppression, native, move):
    """Suppression disables boosts, while physical removal still uses native identity."""
    battle, target, thief = pair(
        "Flame Plate", holder="Arceus" if native else "Mew",
        ability="Multitype" if native else "Synchronize", nickname="Buddy" if native else "Arceus",
    )
    if suppression == "magicroom":
        battle.add_pseudo_weather("magicroom", source=thief)
    elif suppression == "embargo":
        battle.apply_volatile_status(target, "embargo", source=thief)
    else:
        target.ability = "Klutz"  # Eligibility adapter, not a legal native ability claim.
    assert EffectContext.item(target) is None
    attack(battle, thief, target, move)
    assert bool(held(target)) is native
    assert bool(held(thief)) is (not native and move != "Knock Off")
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("move", ("Knock Off", "Trick", "Switcheroo"))
@pytest.mark.parametrize("native_role", (None, "holder", "source"))
@pytest.mark.parametrize("occupied", (False, True))
def test_removal_roles_and_two_item_conservation(move, native_role, occupied):
    """Protect either real native; foreign nickname cannot prevent removal or a swap."""
    battle, target, thief = pair(
        "Flame Plate", holder="Arceus" if native_role == "holder" else "Mew",
        source="Arceus" if native_role == "source" else "Mew",
        nickname="Buddy" if native_role else "Arceus",
        ability="Multitype" if native_role == "holder" else "Synchronize",
    )
    if occupied:
        battle.set_item(thief, "Shed Shell")
    attack(battle, thief, target, move)
    plate, shell = "flameplate", "shedshell" if occupied else ""
    expected = (plate, shell) if native_role else ("", shell) if move == "Knock Off" else (shell, plate)
    assert (held(target), held(thief)) == expected
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("native", (False, True))
def test_genuine_transform_follows_native_base_and_not_copied_appearance(native):
    """Actual copying cannot grant or erase native Plate removal protection."""
    battle, target, thief = pair(
        "Flame Plate", holder="Arceus" if native else "Mew", source="Mew" if native else "Arceus",
        ability="Multitype" if native else "Synchronize",
    )
    attack(battle, target, thief, "Transform")  # Native Arceus adapter is not a learnset claim.
    assert target.transformed
    target.name = "Buddy" if native else "Arceus"
    # Use a third-party non-Arceus source after the copy to isolate holder identity.
    thief.base_species = "Mew"
    thief.species = "Mew"
    attack(battle, thief, target, "Thief")
    assert bool(held(target)) is native
    assert bool(held(thief)) is not native


@pytest.mark.parametrize("ability", ("Multitype", "No Ability"))
def test_native_identity_protection_is_independent_of_ability_and_unknown_names_fail_closed(ability):
    """The reference TakeItem rule has no ability condition; form eligibility does."""
    battle, target, thief = pair("Flame Plate", holder="Arceus", ability=ability)
    attack(battle, thief, target, "Thief")
    assert held(target) == "flameplate" and not held(thief)
    assert str(target.species) == ("Arceus-Fire" if ability == "Multitype" else "Arceus")
    from pokemon.dex import ITEMDEX
    from pokemon.names import resolve_dex_entry

    item = resolve_dex_entry(ITEMDEX, "Flame Plate")
    for malformed in (SimpleNamespace(name="Arceus"), SimpleNamespace(base_species="Arceus-Fake", name="Arceus")):
        assert item.call("onTakeItem", item=item, pokemon=malformed, source=None) is True


def test_occupied_thief_and_sticky_hold_keep_items_unchanged():
    """Ordinary anti-theft rules still precede or accompany Plate eligibility."""
    for occupied in (False, True):
        battle, target, thief = pair("Flame Plate", holder="Gastrodon", ability="Sticky Hold", nickname="Arceus")
        if occupied:
            battle.set_item(thief, "Shed Shell")
        attack(battle, thief, target, "Thief")
        assert held(target) == "flameplate"
        assert held(thief) == ("shedshell" if occupied else "")


@pytest.mark.parametrize("suppressed", (False, True))
def test_physical_take_item_callback_runs_once_with_exact_holder_and_source(suppressed):
    """Including suppressed items must not duplicate callback dispatch or reverse roles."""
    from pokemon.dex.functions.items_funcs import Flameplate

    battle, target, thief = pair("Flame Plate", nickname="Arceus")
    if suppressed:
        battle.add_pseudo_weather("magicroom", source=thief)
    original, calls = Flameplate.onTakeItem, []

    def observe(self, item=None, pokemon=None, source=None):
        """Observe the production hook without substituting its decision."""
        calls.append((pokemon, source))
        return original(self, item=item, pokemon=pokemon, source=source)

    with patch.object(Flameplate, "onTakeItem", observe):
        attack(battle, thief, target, "Thief")
    assert calls == [(target, thief)]
    assert not held(target) and held(thief) == "flameplate"
