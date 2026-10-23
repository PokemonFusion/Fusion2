"""Real damage/protection consumers for a private, already-paid Z descriptor."""

from copy import deepcopy
import random

import pytest

from .helpers import build_battle
from .test_pending_action_effects import action


def strike(*, shield=None, volatile=None, ability=None, ordinary=False):
    """Execute an actual used copy; SQL payment is covered by player-route tests."""
    from pokemon.battle.z_profiles import ZProfiles

    battle, user, foe = build_battle(defender_ability=ability)
    battle.rng = random.Random(12)
    selected = action(battle, user, foe, "Tackle")
    if shield:
        battle.apply_volatile_status(foe, shield, source=foe)
    if volatile:
        battle.apply_volatile_status(foe, volatile, source=foe)
    if not ordinary:
        selected.move = ZProfiles.get("Normalium Z", "Tackle").descriptor(selected.move)
    before = foe.hp, user.hp
    battle.use_move(selected)
    return before[0] - foe.hp, before[1] - user.hp, battle, user, foe


@pytest.mark.parametrize(
    "shield",
    [
        "protect",
        "banefulbunker",
        "burningbulwark",
        "kingsshield",
        "obstruct",
        "silktrap",
        "spikyshield",
    ],
)
def test_personal_shields_quarter_actual_z_damage_without_contact_retaliation(shield):
    """All named personal shields share quartering, not source contact penalties."""
    ordinary, *_ = strike()
    damage, recoil, _, user, _ = strike(shield=shield)
    assert damage == max(1, ordinary // 4) > 0
    assert recoil == 0 and not user.status


def test_accuracy_bypass_keeps_fly_invulnerability_and_substitute():
    """A guaranteed accuracy descriptor still checks target state."""
    damage, *_ = strike(volatile="fly")
    assert damage == 0
    damage, _, _, _, foe = strike(volatile="substitute")
    assert damage == 0
    assert (
        not foe.volatiles.get("substitute") or foe.volatiles["substitute"]["hp"] < foe.max_hp // 4
    )


def test_wonder_guard_and_rough_skin_have_different_real_consumers():
    """Type/ability immunity stays normal while Tackle's contact flag is absent."""
    assert strike(ability="Wonder Guard")[0] == 0
    assert strike(ability="Rough Skin")[1] == 0
    assert strike(ability="Rough Skin", ordinary=True)[1] > 0


def test_descriptor_does_not_mutate_shared_source_or_dex():
    """The paid copy owns its flags/raw metadata independently of Tackle."""
    from pokemon.dex import MOVEDEX
    from pokemon.names import resolve_dex_entry
    from pokemon.battle.z_profiles import ZProfiles

    battle, user, foe = build_battle()
    source = action(battle, user, foe, "Tackle").move
    raw = deepcopy(resolve_dex_entry(MOVEDEX, "Tackle").raw)
    source_raw = deepcopy(source.raw)
    descriptor = ZProfiles.get("normaliumz", "tackle").descriptor(source)
    descriptor.raw["flags"]["example"] = 1
    assert source.raw == source_raw
    assert resolve_dex_entry(MOVEDEX, "Tackle").raw == raw
    assert descriptor._pp_move_name == "Tackle" and descriptor.isZ


@pytest.mark.parametrize(
    "ability,source,profile_type,converted",
    [
        ("Aerilate", "Tackle", "Normal", "Flying"),
        ("Pixilate", "Tackle", "Normal", "Fairy"),
        ("Refrigerate", "Tackle", "Normal", "Ice"),
        ("Galvanize", "Tackle", "Normal", "Electric"),
        ("Normalize", "Ember", "Fire", "Normal"),
        ("Liquid Voice", "Clanging Scales", "Dragon", "Water"),
    ],
)
def test_conversion_preserves_damaging_z_but_changes_the_ordinary_source(
    ability, source, profile_type, converted
):
    """Type immunity observes a fixed Z type; ordinary conversions still execute."""
    from pokemon.battle.z_profiles import ZProfile

    damages = []
    for paid in (False, True):
        battle, user, foe = build_battle(attacker_ability=ability, defender_types=["Ghost"])
        battle.rng = random.Random(12)
        selected = action(battle, user, foe, source)
        if paid:
            selected.move = ZProfile(
                "fixture Z",
                source,
                "private reviewed effect",
                100,
                profile_type,
                "Special",
                sound=ability == "Liquid Voice",
            ).descriptor(selected.move)
        battle.use_move(selected)
        assert selected.move.type == (profile_type if paid else converted)
        damages.append(foe.max_hp - foe.hp)
    if profile_type == "Normal":
        assert damages[0] > 0 == damages[1]
    if ability == "Normalize":
        assert damages[1] > 0 == damages[0]


def test_protection_quarters_actual_substitute_loss_too():
    """The substitute damage adapter must retain the already-paid Z marker."""
    from pokemon.battle.z_profiles import ZProfiles

    losses = []
    for protected in (False, True):
        battle, user, foe = build_battle()
        battle.rng = random.Random(12)
        battle.apply_volatile_status(foe, "substitute", source=foe)
        foe.volatiles["substitute"]["hp"] = 1000
        if protected:
            battle.apply_volatile_status(foe, "protect", source=foe)
        selected = action(battle, user, foe, "Tackle")
        selected.move = ZProfiles.get("Normalium Z", "Tackle").descriptor(selected.move)
        battle.use_move(selected)
        losses.append(1000 - foe.volatiles["substitute"]["hp"])
        assert foe.hp == foe.max_hp
    assert losses[1] == max(1, losses[0] // 4) > 0
