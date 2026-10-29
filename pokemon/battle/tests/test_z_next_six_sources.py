"""Five exact damaging conversions and Calm Mind's ordinary post-bonus effect."""

from copy import deepcopy
import random

import pytest

from .test_diagnosed_item_effects import native_battle
from .test_pending_action_effects import action


PAIRS = (("Firium Z", "Fire Blast", "Inferno Overdrive", "Fire", "Special", 185, "Magmar", 54),
         ("Firium Z", "Flare Blitz", "Inferno Overdrive", "Fire", "Physical", 190, "Growlithe", 45),
         ("Waterium Z", "Hydro Pump", "Hydro Vortex", "Water", "Special", 185, "Gyarados", 40),
         ("Electrium Z", "Thunder", "Gigavolt Havoc", "Electric", "Special", 185, "Pikachu", 41),
         ("Groundium Z", "Earth Power", "Tectonic Rage", "Ground", "Special", 175, "Gastrodon", 39))


@pytest.mark.parametrize("crystal,source,result,kind,category,power,native,level", PAIRS)
def test_exact_damage_profile_and_native_level_learning(crystal, source, result, kind, category, power, native, level):
    """Pin reviewed source identities and real native level boundaries."""
    from pokemon.battle.z_profiles import ZProfiles
    from pokemon.data.generation import get_valid_moves
    from pokemon.names import normalize_name

    profile = ZProfiles.get(crystal, source)
    assert (profile.name, profile.power, profile.move_type, profile.category, profile.target) == (
        result, power, kind, category, "normal")
    assert normalize_name(source) in get_valid_moves(native, level)
    assert normalize_name(source) not in get_valid_moves(native, level - 1)


@pytest.mark.parametrize("crystal,source,result,kind,category,power,native,level", PAIRS)
@pytest.mark.parametrize("protect", (False, True))
def test_paid_z_damage_keeps_source_and_discards_ordinary_recoil_chance_accuracy(crystal, source, result, kind, category, power, native, level, protect):
    """Paid mechanics adapters isolate actual Z hits; SQL qualifies command payment."""
    from pokemon.battle.z_profiles import ZProfiles

    battle, user, foe = native_battle(native, crystal, "Regice")
    selected = action(battle, user, foe, source)
    ordinary = selected.move
    old = deepcopy(ordinary.raw)
    descriptor = ZProfiles.get(crystal, source).descriptor(selected.move)
    assert descriptor.accuracy is True and descriptor.raw["target"] == "normal"
    assert not any(descriptor.raw.get(key) for key in
                   ("secondary", "secondaries", "self", "recoil", "onModifyMove", "multihit", "drain"))
    assert not descriptor.flags.get("contact")
    if protect:
        battle.apply_volatile_status(foe, "protect", source=foe)
    if source == "Thunder":
        battle.setWeather("sunnyday", source=foe)
    selected.move = descriptor
    battle.rng = random.Random(12)
    hp, own_hp = foe.hp, user.hp
    battle.use_move(selected)
    assert foe.hp < hp and not foe.status and user.hp == own_hp
    assert not getattr(battle, "_callback_failures", [])
    # The private descriptor cannot rewrite the selected ordinary move metadata.
    assert ordinary.raw == old


@pytest.mark.parametrize("ability,expected", (("Synchronize", (1, 1)), ("Contrary", (-1, -1)), ("Simple", (2, 2))))
def test_calm_mind_clears_only_negative_stages_then_applies_normal_boosts(ability, expected):
    """Ability adapters qualify ordering; Ralts native access is checked separately."""
    from pokemon.battle.z_effects import ZEffects
    from pokemon.battle.z_profiles import ZProfiles
    from pokemon.data.generation import get_valid_moves

    battle, user, foe = native_battle("Ralts", "Psychium Z", ability=ability)
    user.boosts.update(attack=-2, defense=2, special_attack=-3, special_defense=-1)
    profile = ZProfiles.get("Psychium Z", "Calm Mind")
    assert profile.intrinsic == "clearnegative" and profile.target == "self"
    assert "calmmind" in get_valid_moves("Ralts", 21)
    assert "calmmind" not in get_valid_moves("Ralts", 20)
    selected = action(battle, user, user, "Calm Mind")
    selected.move = profile.descriptor(selected.move, user)
    ZEffects.start(battle, user, profile, selected.move)
    battle.use_move(selected)
    assert (user.boosts["attack"], user.boosts["defense"]) == (0, 2)
    assert (user.boosts["special_attack"], user.boosts["special_defense"]) == expected
