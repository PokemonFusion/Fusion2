"""Observe real execution order and current choices, rather than move history."""

import copy
import logging
import random

import pytest

from .helpers import build_battle, load_modules


@pytest.fixture(autouse=True)
def quiet_log():
    logger = logging.getLogger("battle")
    old = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = old


def action(battle, pokemon, target, name):
    from pokemon.battle.actions import Action, ActionType
    from pokemon.dex.functions.moves.damage_moves import _battle_move_from_name
    move = _battle_move_from_name(name)
    assert move is not None
    return Action(battle.participant_for(pokemon), ActionType.MOVE,
                  battle.participant_for(target), move, pokemon=pokemon, target_pokemon=target)


def doubles():
    battle, user, foe = build_battle()
    modules = load_modules()
    ally = modules["Pokemon"]("Ally", level=50, hp=500, max_hp=500)
    other = modules["Pokemon"]("Other", level=50, hp=500, max_hp=500)
    for pokemon, speed in [(user, 400), (ally, 10), (foe, 200), (other, 100)]:
        pokemon.base_stats = copy.deepcopy(user.base_stats)
        pokemon.base_stats.speed = speed
        pokemon.battle = battle
    battle.participants[0].pokemons.append(ally)
    battle.participants[0].active.append(ally)
    battle.participants[1].pokemons.append(other)
    battle.participants[1].active.append(other)
    for participant in battle.participants:
        participant.max_active = 2
    user.name, foe.name = "User", "Foe"
    battle.rng = random.Random(1)
    battle.show_damage_numbers = True
    return battle, user, ally, foe, other


@pytest.mark.parametrize("name,expected", [("After You", ["User", "Ally", "Foe", "Other"]),
                                            ("Quash", ["User", "Other", "Ally", "Foe"])])
def test_queue_move_changes_actual_remaining_actor_order(name, expected):
    battle, user, ally, foe, other = doubles()
    observed = []
    battle.log_action = observed.append
    actions = [action(battle, user, ally if name == "After You" else foe, name),
               action(battle, ally, foe, "Tackle"), action(battle, foe, user, "Tackle"),
               action(battle, other, user, "Tackle")]
    battle.execute_turn(actions)
    order = [message.split(" used ")[0] for message in observed if " used " in message]
    assert order == expected


@pytest.mark.parametrize("name,foe_move,damage_expected", [("Sucker Punch", "Tackle", True),
    ("Sucker Punch", "Splash", False), ("Upper Hand", "Quick Attack", True),
    ("Upper Hand", "Tackle", False), ("Upper Hand", "Protect", False), ("Me First", "Tackle", True)])
def test_conditional_move_uses_the_pending_choice(name, foe_move, damage_expected):
    battle, user, target = build_battle()
    user.base_stats.speed = 400
    target.base_stats.speed = 50
    from pokemon.dex.functions.moves.damage_moves import _battle_move_from_name
    target.last_move = _battle_move_from_name("Tackle")
    battle.rng = random.Random(1)
    battle.execute_turn([action(battle, user, target, name), action(battle, target, user, foe_move)])
    assert (target.hp < target.max_hp) is damage_expected


def test_sucker_punch_fails_if_the_priority_foe_already_acted():
    battle, user, target = build_battle()
    user.base_stats.speed = 50
    target.base_stats.speed = 400
    battle.rng = random.Random(1)
    battle.execute_turn([action(battle, user, target, "Sucker Punch"), action(battle, target, user, "Quick Attack")])
    assert target.hp == target.max_hp and user.hp < user.max_hp
