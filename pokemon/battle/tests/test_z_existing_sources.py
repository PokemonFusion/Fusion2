"""Two existing generic Z source mappings; player SQL pays the actual PP."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import random

import pytest

from .test_diagnosed_item_effects import native_battle
from .test_pending_action_effects import action

PAIRS = (("Firium Z", "Flamethrower", "Inferno Overdrive", "Fire", "Charizard", 30),
         ("Waterium Z", "Surf", "Hydro Vortex", "Water", "Slowpoke", 30))


@pytest.mark.parametrize("crystal,source,result,kind,native,level", PAIRS)
def test_exact_175_special_normal_profiles(crystal, source, result, kind, native, level):
    """Reference conversion is explicit; no other source is inferred."""
    from pokemon.battle.z_profiles import ZProfiles
    profile = ZProfiles.get(crystal, source)
    assert profile is not None
    assert (profile.name, profile.power, profile.move_type, profile.category, profile.target,
            profile.kind, profile.native) == (result, 175, kind, "Special", "normal", "generic", ())
    assert ZProfiles.get("Firium Z", "Fire Punch") is None


@pytest.mark.parametrize("crystal,source,result,kind,native,level", PAIRS)
def test_private_descriptor_cannot_carry_secondary_or_spread(crystal, source, result, kind, native, level):
    """The ordinary source/dex stay unchanged while the paid copy is single target."""
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
    assert not any(descriptor.raw.get(k) for k in
                   ("secondary", "secondaries", "recoil", "drain", "multihit", "self", "selfSwitch"))
    assert not descriptor.flags.get("contact")
    descriptor.raw["flags"]["private_test"] = 1
    assert selected.move.raw == original
    assert resolve_dex_entry(MOVEDEX, source).raw == dex
    if source == "Surf":
        assert dex["target"] == "allAdjacent"
    else:
        assert dex["secondary"]["status"] == "brn"


def strike(crystal, source, *, protect=False, immune=False):
    """Already-paid descriptor adapter isolates real damage/protection consumers."""
    from pokemon.battle.z_profiles import ZProfiles
    foe = ("Vulpix" if source == "Flamethrower" else "Vaporeon") if immune else "Wailord"
    battle, user, target = native_battle(item=crystal, foe=foe)
    if immune:
        target.ability = "Flash Fire" if source == "Flamethrower" else "Water Absorb"
    if protect:
        battle.apply_volatile_status(target, "protect", source=target)
    selected = action(battle, user, target, source)
    selected.move = ZProfiles.get(crystal, source).descriptor(selected.move)
    battle.rng = random.Random(12)
    hp = target.hp
    battle.use_move(selected)
    assert not target.status
    assert not getattr(battle, "_callback_failures", [])
    return hp - target.hp


@pytest.mark.parametrize("crystal,source,result,kind,native,level", PAIRS)
def test_actual_damage_and_protect_quartering(crystal, source, result, kind, native, level):
    """A real useful hit and shield control must agree, not just assigned fields."""
    damage = strike(crystal, source)
    assert damage > 0
    assert strike(crystal, source, protect=True) == max(1, damage // 4)


@pytest.mark.parametrize("crystal,source,result,kind,native,level", PAIRS)
def test_real_native_ability_immunity(crystal, source, result, kind, native, level):
    """Generic Z conversion preserves the relevant type/ability immunity."""
    assert strike(crystal, source, immune=True) == 0


@pytest.mark.parametrize("crystal,source,result,kind,native,level", PAIRS)
def test_current_native_level_learning_is_available(crystal, source, result, kind, native, level):
    """Chosen ordinary acquisition examples do not depend on a TM or forged move."""
    from pokemon.data.generation import get_valid_moves
    from pokemon.names import normalize_name
    assert normalize_name(source) in get_valid_moves(native, level)
    assert normalize_name(source) not in get_valid_moves(native, level - 1)


def test_sixteen_existing_signature_profiles_are_unchanged():
    """The pre-expansion signature inventory and native fingerprints stay exact."""
    from pokemon.battle.z_signature_pairs import SIGNATURE_PAIRS
    assert len(SIGNATURE_PAIRS) == 16
    digest = hashlib.sha256(json.dumps([asdict(p) for p in SIGNATURE_PAIRS], sort_keys=True).encode()).hexdigest()
    assert digest == "c20d86a160ccf1d2fea55f0c6ad7d0ba951d46e6b195e859b17cee7623926d43"

