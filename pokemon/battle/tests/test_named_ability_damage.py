"""Named abilities from owned Pokemon must affect real move damage."""

import random

import pytest

from .helpers import build_battle, load_modules


def strike(ability, name="Tackle", *, armed=False, status=None):
    """Keep all formula inputs and RNG identical except the named ability."""
    from pokemon.battle.actions import Action, ActionType

    battle, user, target = build_battle(attacker_ability=ability)
    user.status = status
    if armed:
        user.ability_state["flashfire"] = True
    battle.rng = random.Random(0)
    action = Action(battle.participant_for(user), ActionType.MOVE, battle.participant_for(target),
                    load_modules()["BattleMove"](name), pokemon=user)
    battle.use_move(action)
    return target.max_hp - target.hp, user.ability


@pytest.mark.parametrize("ability", ["Huge Power", "Pure Power", "Hustle"])
def test_named_attack_modifier_changes_damage_like_its_dex_entity(ability):
    from pokemon.battle.engine import _resolve_ability

    # Aerial Ace avoids turning Hustle's valid accuracy penalty into a
    # purported damage defect while still exercising its physical Attack hook.
    control, _ = strike("No Ability", "Aerial Ace")
    named, retained = strike(ability, "Aerial Ace")
    entity, _ = strike(_resolve_ability(ability), "Aerial Ace")
    assert named == entity > control > 0
    assert retained == ability


def test_named_hustle_preserves_its_valid_accuracy_failure():
    from pokemon.battle.engine import _resolve_ability

    control, _ = strike("No Ability")
    named, _ = strike("Hustle")
    entity, _ = strike(_resolve_ability("Hustle"))
    assert named == entity == 0
    assert control > 0


def test_named_flash_fire_activation_increases_actual_fire_damage():
    unarmed, _ = strike("Flash Fire", "Ember")
    armed, retained = strike("Flash Fire", "Ember", armed=True)
    assert armed > unarmed > 0
    assert retained == "Flash Fire"


def test_named_guts_requires_status_for_its_damage_bonus():
    control, _ = strike("No Ability")
    healthy, _ = strike("Guts")
    poisoned, _ = strike("Guts", status="psn")
    assert healthy == control > 0
    assert poisoned > healthy


def test_unknown_named_ability_does_not_change_damage_or_mutate_the_name():
    control, _ = strike("No Ability")
    actual, retained = strike("Not A Real Ability")
    assert actual == control
    assert retained == "Not A Real Ability"
