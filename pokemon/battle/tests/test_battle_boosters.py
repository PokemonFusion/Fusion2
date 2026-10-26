"""Actual stage consumers and ability/event boundaries for the named bag boosters."""

from types import SimpleNamespace
import random

import pytest

from pokemon.battle.battle_boosters import BattleBoosters
from pokemon.battle.damage import damage_calc
from pokemon.battle.effect_context import EffectContext
from pokemon.services.battle_items import BattleItemCapability
from .helpers import build_battle
from .test_pending_action_effects import action


class FixedRoll(random.Random):
    """Control accuracy and critical boundaries while keeping real damage consumers."""

    def random(self):
        return 0.9


@pytest.mark.parametrize("item", BattleBoosters.stats)
@pytest.mark.parametrize("ability,amount", [(None, 2), ("Simple", 4), ("Contrary", -2)])
def test_six_items_use_real_change_boost_events(item, ability, amount):
    """Normal ability events modify the result rather than bypassed stage assignment."""
    battle, user, _ = build_battle(attacker_ability=ability)
    assert BattleBoosters.useful(item, user)
    assert BattleBoosters.apply_effect(battle, item, user)
    stat = BattleBoosters.stats[item][2]
    assert user.boosts[stat] == amount
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item", BattleBoosters.stats)
@pytest.mark.parametrize("ability,cap", [(None, 6), ("Simple", 6), ("Contrary", -6)])
def test_caps_are_previewed_without_executing_or_consuming_ability_state(item, ability, cap):
    """A capped effective direction is no effect before a declaration."""
    battle, user, _ = build_battle(attacker_ability=ability)
    user.boosts[BattleBoosters.stats[item][2]] = cap
    user.ripen_active = True
    assert not BattleBoosters.useful(item, user)
    assert user.ripen_active is True
    assert not BattleBoosters.apply_effect(battle, item, user)
    assert user.boosts[BattleBoosters.stats[item][2]] == cap


@pytest.mark.parametrize(
    "item,move,defensive",
    [
        ("X Attack", "Tackle", False),
        ("X Sp. Atk", "Water Gun", False),
        ("X Defense", "Tackle", True),
        ("X Sp. Def", "Water Gun", True),
    ],
)
def test_stages_change_real_damage_for_the_matching_stat(item, move, defensive):
    """Attack/special attack and their matching defenses reach the real damage calculator."""
    battle, user, foe = build_battle()
    selected = action(battle, user, foe, move)
    before = damage_calc(user, foe, selected.move, battle=battle, rng=FixedRoll(1)).debug["damage"][
        0
    ]
    assert BattleBoosters.apply_effect(battle, item, foe if defensive else user)
    after = damage_calc(user, foe, selected.move, battle=battle, rng=FixedRoll(1)).debug["damage"][
        0
    ]
    assert 0 < after < before if defensive else after > before > 0


def test_x_speed_reverses_actual_action_order():
    """The ordinary ordering consumer reads the saved temporary speed stage."""
    battle, user, foe = build_battle()
    user.base_stats.speed, foe.base_stats.speed = 100, 150
    own, other = action(battle, user, foe, "Tackle"), action(battle, foe, user, "Tackle")
    assert EffectContext.speed(user) < EffectContext.speed(foe)
    assert battle.determine_move_order([own, other])[0].pokemon is foe
    BattleBoosters.apply_effect(battle, "X Speed", user)
    assert EffectContext.speed(user) > EffectContext.speed(foe)
    assert battle.determine_move_order([own, other])[0].pokemon is user


def test_x_accuracy_changes_an_actual_miss_into_a_hit():
    """The same legal 85-percent move and roll miss before +2 and connect afterward."""
    outcomes = []
    for boosted in (False, True):
        battle, user, foe = build_battle()
        battle.rng = FixedRoll(1)
        selected = action(battle, user, foe, "Fire Blast")
        if boosted:
            BattleBoosters.apply_effect(battle, "X Accuracy", user)
        battle.use_move(selected)
        outcomes.append(foe.max_hp - foe.hp)
        assert not getattr(battle, "_callback_failures", [])
    assert outcomes[0] == 0 < outcomes[1]


@pytest.mark.parametrize("suppression", ["magicroom", "klutz", "healblock"])
def test_bag_boost_does_not_inherit_held_or_healing_suppression(suppression):
    """Magic Room/Klutz/Heal Block cannot suppress a bag's stage event."""
    battle, user, _ = build_battle(attacker_ability="Klutz" if suppression == "klutz" else None)
    if suppression == "magicroom":
        battle.field.pseudo_weather["magicroom"] = {"duration": 5}
    elif suppression == "healblock":
        user.volatiles["healblock"] = {"duration": 5}
    BattleBoosters.target(user)
    assert BattleBoosters.apply_effect(battle, "X Attack", user)
    assert user.boosts["attack"] == 2


@pytest.mark.parametrize("item", ["X", "X HP", "X Special", "Rare Candy", "Guard Spec. Plus"])
def test_no_generic_booster_or_future_item_fallback(item):
    """Only this reviewed six-name batch is enabled by the foundation."""
    assert not BattleBoosters.supports(item)


@pytest.mark.parametrize("participants,multi", [(4, True), (3, False), (2, True)])
def test_unreviewed_formats_reject_at_the_shared_capability_boundary(participants, multi):
    """Saved actions cannot bypass the command's format restrictions."""
    battle = SimpleNamespace(
        type=SimpleNamespace(name="PVP"),
        multi=multi,
        participants=[SimpleNamespace(max_active=1)] * participants,
    )
    with pytest.raises(ValueError, match="two-participant"):
        BattleItemCapability.validate("X Attack", battle=battle)


@pytest.mark.parametrize("item", [*BattleBoosters.stats, "direhit", "guardspec"])
def test_all_eight_manual_names_have_discoverable_battle_only_metadata(item):
    """Named command capability and normal inventory/itemdex metadata agree."""
    from pokemon.items import BATTLE_BOOSTER_ITEMS
    from pokemon.middleware import get_item_by_name

    data = BATTLE_BOOSTER_ITEMS[item]
    assert get_item_by_name(data.name)[1] is data
    assert data.raw["battleOnly"] is True and data.raw["isPokeball"] is False
    assert data.raw["price"] == (1500 if item == "guardspec" else 1000)
    assert "+item" in data.desc and BattleBoosters.supports(data.name)
