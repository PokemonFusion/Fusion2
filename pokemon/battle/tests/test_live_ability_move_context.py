"""Fresh positive and negative reproductions for observed ability failures."""

import logging
import random

import pytest

from .helpers import build_battle, load_modules


@pytest.fixture(autouse=True)
def quiet_battle_log():
    """Do not mix offline diagnostic events into local gameplay logs."""
    logger = logging.getLogger("battle")
    previous = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = previous


def use(battle, user, target, name):
    """Use the actual named move pipeline with a private deterministic RNG."""
    from pokemon.battle.actions import Action, ActionType

    battle.rng = random.Random(0)
    move = load_modules()["BattleMove"](name)
    battle.use_move(Action(battle.participant_for(user), ActionType.MOVE,
                           battle.participant_for(target), move, pokemon=user))
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("ability", ["Scrappy", "Mind's Eye"])
@pytest.mark.parametrize("move,types", [("Tackle", ["Ghost"]), ("Low Kick", ["Ghost", "Dark"])])
def test_ghost_bypass_is_retained_by_the_actual_damage_move(ability, move, types):
    battle, user, target = build_battle(attacker_ability=ability, defender_types=types)
    use(battle, user, target, move)
    assert target.hp < target.max_hp


@pytest.mark.parametrize("ability", [None, "Scrappy", "Mind's Eye"])
def test_ghost_bypass_does_not_remove_unrelated_ground_immunity(ability):
    battle, user, target = build_battle(attacker_ability=ability, defender_types=["Flying"])
    use(battle, user, target, "Mud-Slap")
    assert target.hp == target.max_hp


def test_long_reach_removes_contact_only_for_its_own_move_use():
    battle, user, target = build_battle(attacker_ability="Long Reach", defender_ability="Rough Skin")
    use(battle, user, target, "Tackle")
    assert target.hp < target.max_hp and user.hp == user.max_hp
    user.ability = "No Ability"
    use(battle, user, target, "Tackle")
    assert user.hp < user.max_hp


@pytest.mark.parametrize("screen,attack", [("Reflect", "Tackle"), ("Light Screen", "Water Gun")])
def test_infiltrator_bypasses_screens_without_removing_the_screen(screen, attack):
    battle, user, target = build_battle(attacker_ability="Infiltrator")
    use(battle, target, target, screen)
    use(battle, user, target, attack)
    infiltrating = target.max_hp - target.hp
    target.hp = target.max_hp
    user.ability = "No Ability"
    use(battle, user, target, attack)
    assert target.max_hp - target.hp < infiltrating
    assert target.side.conditions


def test_infiltrator_bypasses_substitute_and_preserves_its_hp():
    battle, user, target = build_battle(attacker_ability="Infiltrator")
    use(battle, target, target, "Substitute")
    previous = target.hp
    sub_hp = target.volatiles["substitute"]["hp"]
    use(battle, user, target, "Tackle")
    assert target.hp < previous
    assert target.volatiles["substitute"]["hp"] == sub_hp


@pytest.mark.parametrize("ability", ["Rock Head", "Magic Guard"])
@pytest.mark.parametrize("substitute", [False, True])
def test_recoil_passes_the_holders_guard_even_when_hitting_a_substitute(ability, substitute):
    battle, user, target = build_battle(attacker_ability=ability)
    if substitute:
        use(battle, target, target, "Substitute")
    use(battle, user, target, "Take Down")
    assert user.hp == user.max_hp


@pytest.mark.parametrize("ability", ["Rock Head", "Magic Guard"])
def test_recoil_guards_do_not_stop_an_opponents_direct_move(ability):
    battle, user, target = build_battle(defender_ability=ability)
    use(battle, user, target, "Tackle")
    assert target.hp < target.max_hp


@pytest.mark.parametrize("ability", ["Cloud Nine", "Air Lock"])
def test_weather_damage_modifiers_are_suppressed_without_removing_weather(ability):
    battle, user, target = build_battle(attacker_ability=ability)
    use(battle, user, user, "Sunny Day")
    use(battle, user, target, "Flamethrower")
    suppressed = target.max_hp - target.hp
    target.hp = target.max_hp
    user.ability = "No Ability"
    use(battle, user, target, "Flamethrower")
    assert target.max_hp - target.hp > suppressed
    assert battle.field.weather == "sunnyday"


def test_magic_guard_blocks_contact_damage_without_blocking_the_attack():
    battle, user, target = build_battle(attacker_ability="Magic Guard", defender_ability="Rough Skin")
    use(battle, user, target, "Tackle")
    assert target.hp < target.max_hp and user.hp == user.max_hp


@pytest.mark.parametrize("ally,allowed", [(False, False), (True, True)])
def test_unnerve_checks_real_berry_metadata_and_only_opposing_holders(ally, allowed):
    battle, user, target = build_battle(attacker_ability="Unnerve")
    if ally:
        target = load_modules()["Pokemon"]("Ally", hp=100, max_hp=200)
        target.battle = battle
        part = battle.participant_for(user)
        part.pokemons.append(target)
        part.active.append(target)
        target.side = part.side
    target.hp = 100
    assert battle.set_item(target, "Oran Berry")
    assert battle.eat_item(target) is allowed
    assert bool(battle._holder_item(target)) is (not allowed)


def test_non_suppressing_holder_can_remain_when_one_of_two_suppressors_leaves():
    battle, user, target = build_battle(attacker_ability="Cloud Nine", defender_ability="Air Lock")
    use(battle, user, user, "Sunny Day")
    assert user.effective_weather() == ""
    user.ability = "No Ability"
    assert user.effective_weather() == ""
    target.hp = 0
    assert user.effective_weather() == "sunnyday"
