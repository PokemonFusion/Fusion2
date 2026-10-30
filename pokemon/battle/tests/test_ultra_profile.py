"""Pinned Ultra metadata, legitimate Photon access and actual reference category rules."""

import pytest

from pokemon.battle.battledata import Pokemon
from pokemon.battle.ultra_profile import UltraProfile
from pokemon.dex.entities import Stats


def test_reviewed_descriptor_has_one_explicit_registry_pair():
    """A typed profile alone grants neither a native source nor a public action."""
    from pokemon.battle.z_profiles import ZProfiles

    profile = UltraProfile.checked()
    assert profile.version == 1 and len(profile.fingerprint) == 64
    assert profile.z_profile().power == 200
    assert profile.z_profile().ignore_ability
    assert ZProfiles.get(profile.crystal, profile.source) == profile.z_profile()
    assert ZProfiles.get(profile.crystal, "Tackle") is None


@pytest.mark.parametrize(
    "level,expected", [(49, False), (50, True), (71, True), (72, True), (True, False), (0, False)]
)
def test_photon_preparation_keeps_existing_cross_generation_access(level, expected):
    """The current legitimate source becomes available at50, without granting it."""
    assert UltraProfile.source_is_learnable(level) is expected


@pytest.mark.parametrize(
    "attack,special,attack_stage,special_stage,expected",
    [
        (100, 100, 0, 0, "Special"),
        (101, 100, 0, 0, "Physical"),
        (100, 150, 2, 0, "Physical"),
        (150, 100, 0, 2, "Special"),
        (150, 100, -2, 0, "Special"),
        (100, 150, 0, -2, "Physical"),
        (100, 100, 2, 2, "Special"),
    ],
)
def test_category_uses_actual_stored_stats_and_raw_stages(
    attack, special, attack_stage, special_stage, expected
):
    """A stage can change the category; exact ties remain Special."""
    pokemon = Pokemon("Necrozma-Ultra", level=50, nature="Hardy", ivs=[0] * 6, evs=[0] * 6)
    pokemon.base_stats = Stats(
        hp=pokemon.max_hp,
        attack=attack,
        defense=100,
        special_attack=special,
        special_defense=100,
        speed=100,
    )
    pokemon.boosts.update(atk=attack_stage, spa=special_stage)
    assert UltraProfile.category(pokemon) == expected


def test_choice_band_huge_power_and_modifyboost_do_not_choose_signature_category():
    """Real effects that raise Attack damage do not alter this stored-stat comparison."""
    from .test_diagnosed_item_effects import native_battle

    _, pokemon, _ = native_battle(item="Choice Band", ability="Huge Power")
    pokemon.base_stats = Stats(
        hp=pokemon.max_hp,
        attack=100,
        defense=100,
        special_attack=101,
        special_defense=100,
        speed=100,
    )
    assert UltraProfile.category(pokemon) == "Special"
    pokemon.boosts["atk"] = 1
    assert UltraProfile.category(pokemon) == "Physical"


def signature_damage(
    *, ability="Neuroforce", foe="Venusaur", protected=False, wonder=False, stages=None
):
    """Effect-only native adapter; ordinary SQL cases prove acquisition and payment."""
    from .test_diagnosed_item_effects import native_battle
    from pokemon.battle.actions import Action, ActionType
    from pokemon.battle.engine import BattleMove, _resolve_ability

    battle, source, target = native_battle(name="Necrozma-Ultra", ability=ability, foe=foe)
    if stages:
        source.boosts.update(stages)
    if wonder:
        target.ability = _resolve_ability("Wonder Guard")
    if protected:
        target.volatiles["protect"] = {"duration": 1, "source": target}
    move = UltraProfile.checked().z_profile().descriptor(BattleMove("Photon Geyser"), source)
    action = Action(
        battle.participant_for(source),
        ActionType.MOVE,
        battle.participant_for(target),
        move=move,
        pokemon=source,
        target_pokemon=target,
    )
    hp = target.hp
    battle.use_move(action)
    assert not getattr(battle, "_callback_failures", [])
    return hp - target.hp, move, source


def test_actual_neuroforce_increases_super_effective_signature_damage():
    """Canonical Neuroforce modifies real damage, only while the ability is active."""
    ordinary, _, _ = signature_damage(ability="Synchronize")
    boosted, move, _ = signature_damage()
    assert ordinary > 0 and boosted > ordinary
    assert abs(boosted - ordinary * 1.25) <= 2
    assert move.raw["ignoreAbility"] is True
    assert move.accuracy is True


def test_signature_does_not_turn_neutral_damage_into_neuroforce_bonus():
    """A neutral native defender provides the meaningful negative ability control."""
    ordinary, _, _ = signature_damage(ability="Synchronize", foe="Wailord")
    boosted, _, _ = signature_damage(foe="Wailord")
    assert ordinary == boosted and ordinary > 0


def test_signature_ignores_wonder_guard_but_respects_dark_immunity():
    """Ability-ignore does not bypass actual Psychic type immunity."""
    neutral, _, _ = signature_damage(foe="Wailord")
    wonder, _, _ = signature_damage(foe="Wailord", wonder=True)
    immune, _, _ = signature_damage(foe="Umbreon", wonder=True)
    assert wonder == neutral and wonder > 0
    assert immune == 0


def test_signature_personal_protect_quarters_real_damage():
    """The paid descriptor participates in the ordinary protection boundary."""
    ordinary, _, _ = signature_damage(foe="Wailord")
    protected, _, _ = signature_damage(foe="Wailord", protected=True)
    assert ordinary > 0 and protected == max(1, ordinary // 4)


@pytest.mark.parametrize("stages,expected", [({"atk": 2}, "Physical"), ({"spa": 2}, "Special")])
def test_actual_signature_descriptor_selects_stage_aware_category(stages, expected):
    """The chosen category reaches the actual engine descriptor, beyond the helper."""
    damage, move, _ = signature_damage(foe="Wailord", stages=stages)
    assert move.raw["category"] == expected and move.category == expected
    assert damage > 0
