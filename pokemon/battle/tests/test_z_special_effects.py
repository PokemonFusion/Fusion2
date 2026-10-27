"""Damage consumers for reviewed status/signature Z intrinsics and negatives."""

from copy import deepcopy
import random

import pytest

from .helpers import build_battle
from .test_pending_action_effects import action


class FixedRoll(random.Random):
    """Expose the critical boundary while keeping the real damage calculator."""

    def __init__(self, value):
        super().__init__(1)
        self.value = value

    def random(self):
        return self.value


@pytest.mark.parametrize("value,critical", [(0.25, True), (0.75, False)])
@pytest.mark.parametrize("effect", ["cap", "tailwind"])
def test_two_stage_critical_effect_uses_real_half_probability(value, critical, effect):
    """Ratio-three dex data is not PF2 stage three's guaranteed critical."""
    from pokemon.battle.damage import damage_calc
    from pokemon.battle.z_profiles import ZProfiles
    from pokemon.battle.z_effects import ZEffects

    battle, user, target = build_battle()
    selected = action(battle, user, target, "Thunderbolt" if effect == "cap" else "Tackle")
    if effect == "cap":
        selected.move = ZProfiles.get("Pikashunium Z", "Thunderbolt").descriptor(selected.move)
    else:
        profile = ZProfiles.get("Flyinium Z", "Tailwind")
        ZEffects.start(battle, user, profile, profile.descriptor(selected.move, user))
    result = damage_calc(user, target, selected.move, battle=battle, rng=FixedRoll(value))
    assert result.debug["critical"] == [critical]
    assert result.debug["damage"][0] > 0


@pytest.mark.parametrize("hp", [1, 2, 3, 7, 13, 101, 999])
@pytest.mark.parametrize("protected", [False, True])
def test_guardian_fraction_and_protected_rounding_on_actual_damage(hp, protected):
    """The fixed fraction is applied before the special protected rounding."""
    from pokemon.battle.z_profiles import ZProfiles

    battle, user, target = build_battle()
    target.hp = target.max_hp = hp
    if protected:
        battle.apply_volatile_status(target, "protect", source=target)
    selected = action(battle, user, target, "Nature's Madness")
    selected.move = ZProfiles.get("Tapunium Z", "Nature's Madness").descriptor(selected.move)
    battle.use_move(selected)
    fraction = 3 * hp // 4
    expected = max(1, (fraction + 1) // 4 if protected else fraction)
    assert hp - target.hp == expected


@pytest.mark.parametrize(
    "crystal,source", [("Lunalium Z", "Moongeist Beam"), ("Solganium Z", "Sunsteel Strike")]
)
def test_signature_bypasses_breakable_ability_but_keeps_shadow_shield(crystal, source):
    """Intrinsic ignoreAbility obeys the ordinary nonbreakable ability boundary."""
    from pokemon.battle.z_profiles import ZProfiles

    losses = []
    for ability in (None, "Wonder Guard", "Shadow Shield"):
        battle, user, target = build_battle(defender_ability=ability, defender_types=["Water"])
        battle.rng = random.Random(12)
        selected = action(battle, user, target, source)
        selected.move = ZProfiles.get(crystal, source).descriptor(selected.move)
        battle.use_move(selected)
        losses.append(target.max_hp - target.hp)
    assert losses[0] == losses[1] > losses[2] > 0


@pytest.mark.parametrize(
    "crystal,source,terrain",
    [("Lycanium Z", "Stone Edge", None), ("Mewnium Z", "Psychic", "psychicterrain")],
)
def test_signature_terrain_effect_reaches_substitute_only_after_real_damage(
    crystal, source, terrain
):
    """A substitute hit changes terrain without damaging its holder."""
    from pokemon.battle.z_profiles import ZProfiles

    for immune in (False, True):
        battle, user, target = build_battle(defender_ability="Wonder Guard" if immune else None)
        battle.setTerrain("electricterrain", source=target)
        battle.apply_volatile_status(target, "substitute", source=target)
        target.volatiles["substitute"]["hp"] = 1000
        selected = action(battle, user, target, source)
        selected.move = ZProfiles.get(crystal, source).descriptor(selected.move)
        battle.use_move(selected)
        assert target.hp == target.max_hp
        assert battle.field.terrain == ("electricterrain" if immune else terrain)


def test_signature_copy_has_only_reviewed_intrinsics_and_leaves_dex_unchanged():
    """No source-only recoil/recharge/trapping/theft/Defense drop is copied."""
    from pokemon.battle.z_signature_pairs import SIGNATURE_PAIRS
    from pokemon.dex import MOVEDEX
    from pokemon.names import resolve_dex_entry

    battle, user, target = build_battle()
    for profile in SIGNATURE_PAIRS:
        source = action(battle, user, target, profile.source).move
        before = deepcopy(resolve_dex_entry(MOVEDEX, profile.source).raw)
        selected = profile.descriptor(source)
        assert not any(
            selected.raw.get(key)
            for key in ("recoil", "selfdestruct", "ignoreDefensive", "volatileStatus", "onHit")
        )
        assert selected.priority == 0 and selected.accuracy is True
        assert resolve_dex_entry(MOVEDEX, profile.source).raw == before


@pytest.mark.parametrize("mode", ["both-immune", "protected", "sound-substitute"])
def test_soulblaze_resolves_each_target_and_boosts_once_after_any_real_hit(mode):
    """Independent target guards cannot grant two boosts or cancel a legal peer."""
    from .test_pending_action_effects import doubles
    from pokemon.battle.z_profiles import ZProfiles
    from pokemon.battle.z_spread import ZSpread

    battle, user, ally, foe, other = doubles()
    selected = action(battle, user, foe, "Clanging Scales")
    selected.move = ZProfiles.get("Kommonium Z", "Clanging Scales").descriptor(selected.move)
    before = foe.hp, other.hp
    if mode == "both-immune":
        foe.types = other.types = ["Fairy"]
    if mode == "protected":
        battle.apply_volatile_status(foe, "protect", source=foe)
    if mode == "sound-substitute":
        battle.apply_volatile_status(foe, "substitute", source=foe)
        foe.volatiles["substitute"]["hp"] = 1000
    ZSpread.execute(battle, selected)
    if mode == "both-immune":
        assert (foe.hp, other.hp) == before
        assert user.boosts["defense"] == user.boosts["attack"] == 0
    else:
        assert foe.hp < before[0] and other.hp < before[1]
        assert user.boosts["defense"] == user.boosts["attack"] == 1
    if mode == "sound-substitute":
        assert foe.volatiles["substitute"]["hp"] == 1000


@pytest.mark.parametrize(
    "row_species,current,transformed,proof",
    [
        ("Pikachu", "Pikachu", False, None),
        ("Pikachu-World", "Pikachu-World", False, None),
        ("Mimikyu-Busted", "Mimikyu-Busted", False, None),
        (
            "Mimikyu",
            "Mimikyu-Busted",
            False,
            {"ref": "owned:foreign", "species": "Mimikyu", "form": "Mimikyu-Busted"},
        ),
        (
            "Mimikyu",
            "Mimikyu-Busted",
            True,
            {"ref": "owned:fixture", "species": "Mimikyu", "form": "Mimikyu-Busted"},
        ),
    ],
)
def test_unqualified_native_forms_cannot_use_signature(row_species, current, transformed, proof):
    """A nickname, unlisted cap, direct Busted grant or copied proof cannot qualify."""
    from types import SimpleNamespace
    from pokemon.battle.z_moves import ZMoves
    from pokemon.battle.z_profiles import ZProfiles

    profile = (
        ZProfiles.get("Pikashunium Z", "Thunderbolt")
        if row_species.startswith("Pikachu")
        else ZProfiles.get("Mimikium Z", "Play Rough")
    )
    user = SimpleNamespace(
        species=current,
        model_id="owned:fixture",
        transformed=transformed,
        native_origin={"disguise_busted": proof},
    )
    with pytest.raises(ValueError):
        ZMoves.native(profile, user, {"species": row_species})


@pytest.mark.parametrize("species", ["Mimikyu", "Mimikyu-Totem"])
def test_disguise_native_proof_survives_real_switch_entry_reset(species):
    """The real ability-state reset must not erase an earned native form proof."""
    from pokemon.battle.z_moves import ZMoves
    from pokemon.battle.z_profiles import ZProfiles

    battle, user, target = build_battle(
        defender_ability="Disguise", defender_types=["Ghost", "Fairy"]
    )
    target.species = target.base_species = species
    target.model_id = "owned:fixture"
    target.native_origin = {"ref": target.model_id, "species": species}
    battle.use_move(action(battle, user, target, "Bite"))
    profile = ZProfiles.get("Mimikium Z", "Play Rough")
    ZMoves.native(profile, target, {"species": species})
    proof = deepcopy(target.native_origin)
    battle.on_switch_out(target)
    battle.on_enter_battle(target)
    assert target.native_origin == proof
    ZMoves.native(profile, target, {"species": species})
