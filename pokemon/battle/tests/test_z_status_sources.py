"""Exact status Z profiles retain useful ordinary HP/status/protection effects."""

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json

import pytest

from .test_diagnosed_item_effects import native_battle
from .test_pending_action_effects import action

PAIRS = (
    ("Normalium Z", "Recover", "Starmie", 1, "self", "clearnegative", ()),
    ("Flyinium Z", "Roost", "Pidgeot", 44, "self", "clearnegative", ()),
    ("Normalium Z", "Protect", "Pelipper", 1, "self", "clearnegative", ()),
    ("Poisonium Z", "Toxic", "Clodsire", 40, "normal", "boost", (("def", 1),)),
    ("Electrium Z", "Thunder Wave", "Mareep", 4, "normal", "boost", (("spd", 1),)),
    ("Grassium Z", "Synthesis", "Bulbasaur", 27, "self", "clearnegative", ()),
)


@pytest.mark.parametrize("crystal,source,native,level,target,intrinsic,bonus", PAIRS)
def test_exact_status_profile_and_native_learning(
    crystal, source, native, level, target, intrinsic, bonus
):
    """Only the six named profiles are accepted with actual native move access."""
    from pokemon.battle.z_profiles import ZProfiles
    from pokemon.data.generation import get_valid_moves
    from pokemon.names import normalize_name

    profile = ZProfiles.get(crystal, source)
    assert profile is not None
    assert (profile.kind, profile.category, profile.target, profile.intrinsic, profile.bonus) == (
        "status",
        "Status",
        target,
        intrinsic,
        bonus,
    )
    assert normalize_name(source) in get_valid_moves(native, level)
    if level > 1:
        assert normalize_name(source) not in get_valid_moves(native, level - 1)


@pytest.mark.parametrize("crystal,source,native,level,target,intrinsic,bonus", PAIRS)
def test_private_status_copy_preserves_ordinary_data(
    crystal, source, native, level, target, intrinsic, bonus
):
    """Base callbacks, priority and target survive without changing the shared dex."""
    from pokemon.battle.z_profiles import ZProfiles
    from pokemon.dex import MOVEDEX
    from pokemon.names import resolve_dex_entry

    battle, user, foe = native_battle(native, crystal)
    original = action(battle, user, user if target == "self" else foe, source).move
    before = deepcopy(resolve_dex_entry(MOVEDEX, source).raw)
    copy = ZProfiles.get(crystal, source).descriptor(original, user)
    assert copy is not original and copy.raw["target"] == target
    assert copy.priority == original.priority and copy.onHit == original.onHit
    assert copy._pp_move_name == source and copy._z_paid
    copy.raw["flags"]["private_probe"] = 1
    assert resolve_dex_entry(MOVEDEX, source).raw == before


@pytest.mark.parametrize("crystal,source,native,level,target,intrinsic,bonus", PAIRS)
def test_bonus_and_actual_ordinary_effect(crystal, source, native, level, target, intrinsic, bonus):
    """A paid offline adapter observes real HP/status or protection after the bonus."""
    from pokemon.battle.z_profiles import ZProfiles
    from pokemon.battle.z_effects import ZEffects

    battle, user, foe = native_battle(native, crystal, hp_fraction=0.25)
    user.boosts.update(attack=-2, defense=2, special_defense=-1)
    before = user.hp
    selected = action(battle, user, user if target == "self" else foe, source)
    # Production binds ordinary callbacks before ZMoves.begin creates the copy.
    from pokemon.battle.engine import _resolve_callback
    from pokemon.dex.functions import moves_funcs

    if selected.move.raw.get("onHit"):
        selected.move.onHit = _resolve_callback(selected.move.raw["onHit"], moves_funcs)
    profile = ZProfiles.get(crystal, source)
    assert profile is not None
    selected.move = profile.descriptor(selected.move, user)
    ZEffects.start(battle, user, profile, selected.move)
    battle.use_move(selected)
    if intrinsic == "clearnegative":
        assert (
            user.boosts["attack"] == 0
            and user.boosts["defense"] == 2
            and user.boosts["special_defense"] == 0
        )
    elif source == "Toxic":
        assert user.boosts["defense"] == 3 and foe.status == "tox"
    else:
        assert user.boosts["special_defense"] == 0 and foe.status == "par"
    if source in {"Recover", "Roost", "Synthesis"}:
        assert user.hp == min(user.max_hp, before + user.max_hp // 2)
    elif source == "Protect":
        hp = user.hp
        battle.use_move(action(battle, foe, user, "Tackle"))
        assert user.hp == hp and user.volatiles.get("protect")
    assert not getattr(battle, "_callback_failures", [])


def test_original_eight_status_and_sixteen_signatures_stay_exact():
    """New status entries cannot rewrite earlier bonus or native-pair profiles."""
    from pokemon.battle.z_status_pairs import STATUS_PAIRS
    from pokemon.battle.z_signature_pairs import SIGNATURE_PAIRS

    assert len(STATUS_PAIRS) == 15 and len(SIGNATURE_PAIRS) == 16
    for profiles, digest in [
        (STATUS_PAIRS[:8], "0b86cdd34a0a26058ef128c66a40c7d116af104a362ec5ec25bfe91826a1d02d"),
        (SIGNATURE_PAIRS, "c20d86a160ccf1d2fea55f0c6ad7d0ba951d46e6b195e859b17cee7623926d43"),
    ]:
        assert (
            hashlib.sha256(
                json.dumps([asdict(p) for p in profiles], sort_keys=True).encode()
            ).hexdigest()
            == digest
        )


def test_z_thunder_wave_keeps_bonus_before_ground_immunity():
    """An already-paid descriptor keeps its bonus while Ground blocks the base status."""
    from pokemon.battle.z_profiles import ZProfiles
    from pokemon.battle.z_effects import ZEffects

    battle, user, target = native_battle("Mareep", "Electrium Z", foe="Diglett")
    user.boosts["special_defense"] = -1
    selected = action(battle, user, target, "Thunder Wave")
    profile = ZProfiles.get("Electrium Z", "Thunder Wave")
    selected.move = profile.descriptor(selected.move, user)
    ZEffects.start(battle, user, profile, selected.move)
    battle.use_move(selected)
    assert user.boosts["special_defense"] == 0 and not target.status
