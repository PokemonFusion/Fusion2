"""Six exact ordinary special Z sources, not a catalog-wide conversion rule."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import random

import pytest

from .test_diagnosed_item_effects import native_battle
from .test_pending_action_effects import action

PAIRS = (
    ("Electrium Z", "Thunderbolt", "Gigavolt Havoc", "Electric", "Pikachu", 26, 175),
    ("Icium Z", "Ice Beam", "Subzero Slammer", "Ice", "Lapras", 31, 175),
    ("Grassium Z", "Energy Ball", "Bloom Doom", "Grass", "Voltorb-Hisui", 29, 175),
    ("Psychium Z", "Psychic", "Shattered Psyche", "Psychic", "Kadabra", 35, 175),
    ("Ghostium Z", "Shadow Ball", "Never-Ending Nightmare", "Ghost", "Gastly", 29, 160),
    ("Poisonium Z", "Sludge Bomb", "Acid Downpour", "Poison", "Grimer", 26, 175),
)
IMMUNE = {"Electric": "Jolteon", "Ice": "Shedinja", "Grass": "Gogoat",
          "Psychic": "Umbreon", "Ghost": "Eevee", "Poison": "Empoleon"}


@pytest.mark.parametrize("crystal,source,result,kind,native,level,power", PAIRS)
def test_exact_special_normal_profiles(crystal, source, result, kind, native, level, power):
    """Pin all six reference powers, types and single-target descriptors."""
    from pokemon.battle.z_profiles import ZProfiles

    profile = ZProfiles.get(crystal, source)
    assert profile is not None
    assert (profile.name, profile.power, profile.move_type, profile.category,
            profile.target, profile.kind, profile.native) == (
                result, power, kind, "Special", "normal", "generic", ())
    assert ZProfiles.get("Firium Z", "Fire Blast") is None


@pytest.mark.parametrize("crystal,source,result,kind,native,level,power", PAIRS)
def test_private_special_descriptor_preserves_ordinary_source(crystal, source, result, kind, native, level, power):
    """No secondary, self, spread or descriptor mutation leaks to a source/dex row."""
    from pokemon.battle.z_profiles import ZProfiles
    from pokemon.dex import MOVEDEX
    from pokemon.names import resolve_dex_entry

    battle, user, target = native_battle(item=crystal)
    selected = action(battle, user, target, source)
    original = deepcopy(selected.move.raw)
    dex = deepcopy(resolve_dex_entry(MOVEDEX, source).raw)
    descriptor = ZProfiles.get(crystal, source).descriptor(selected.move)
    assert descriptor.raw["target"] == "normal" and descriptor.accuracy is True
    assert descriptor._pp_move_name == source and descriptor._z_paid
    assert not any(descriptor.raw.get(key) for key in (
        "secondary", "secondaries", "self", "selfSwitch", "recoil", "drain", "multihit"))
    assert not descriptor.flags.get("contact")
    descriptor.raw["flags"]["private_probe"] = 1
    assert selected.move.raw == original and resolve_dex_entry(MOVEDEX, source).raw == dex


def strike(crystal, source, kind, *, protect=False, immune=False):
    """An already-paid offline descriptor isolates damage and native prevention."""
    from pokemon.battle.z_profiles import ZProfiles
    from pokemon.dex import POKEDEX
    from pokemon.names import resolve_dex_entry

    foe = IMMUNE[kind] if immune else "Regice"
    battle, user, target = native_battle(item=crystal, foe=foe)
    if immune:
        target.ability = resolve_dex_entry(POKEDEX, foe).raw["abilities"]["0"]
    if protect:
        battle.apply_volatile_status(target, "protect", source=target)
    selected = action(battle, user, target, source)
    selected.move = ZProfiles.get(crystal, source).descriptor(selected.move)
    battle.rng = random.Random(12)
    hp = target.hp
    battle.use_move(selected)
    assert not target.status and not getattr(battle, "_callback_failures", [])
    return hp - target.hp


@pytest.mark.parametrize("crystal,source,result,kind,native,level,power", PAIRS)
def test_real_damage_and_matching_protect(crystal, source, result, kind, native, level, power):
    """Real damage and its quartered shield control agree under the same conditions."""
    damage = strike(crystal, source, kind)
    assert damage > 0
    assert strike(crystal, source, kind, protect=True) == max(1, damage // 4)


@pytest.mark.parametrize("crystal,source,result,kind,native,level,power", PAIRS)
def test_real_native_type_and_ability_immunities(crystal, source, result, kind, native, level, power):
    """Volt Absorb, Wonder Guard, Sap Sipper and native types still prevent damage."""
    assert strike(crystal, source, kind, immune=True) == 0


@pytest.mark.parametrize("crystal,source,result,kind,native,level,power", PAIRS)
def test_actual_native_level_learning_boundary(crystal, source, result, kind, native, level, power):
    """Chosen examples use current native level access, not a forged learned slot."""
    from pokemon.data.generation import get_valid_moves
    from pokemon.names import normalize_name

    assert normalize_name(source) in get_valid_moves(native, level)
    assert normalize_name(source) not in get_valid_moves(native, level - 1)


def test_old_generic_and_signature_fingerprints_are_preserved():
    """Exactly six appended sources leave the original nineteen and signatures intact."""
    from pokemon.battle.z_generic_pairs import GENERIC_PAIRS
    from pokemon.battle.z_signature_pairs import SIGNATURE_PAIRS
    from pokemon.battle.z_profiles import ZProfiles

    def fingerprint(profiles):
        """Freeze the full reviewed profile data, including native and effect fields."""
        return hashlib.sha256(json.dumps([asdict(p) for p in profiles], sort_keys=True).encode()).hexdigest()

    assert len(GENERIC_PAIRS) >= 25 and len(ZProfiles.accepted) == 1
    assert fingerprint(GENERIC_PAIRS[:19]) == "8531fef86a1f635abd4e8951b92a0a4c9d3161975f756b9ec7d59656fa01df78"
    assert len(SIGNATURE_PAIRS) == 16
    assert fingerprint(SIGNATURE_PAIRS) == "c20d86a160ccf1d2fea55f0c6ad7d0ba951d46e6b195e859b17cee7623926d43"
