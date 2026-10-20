"""Retaliation failures reproduced through ordinary local QA battle commands."""

import random

import pytest

from .helpers import build_battle, load_modules, make_stats


def use(battle, user, target, name):
    """Use real dex callbacks through the player's normal engine entry."""
    from pokemon.battle.actions import Action, ActionType

    move = load_modules()["BattleMove"](name, pp=10)
    user.moves = [move]
    action = Action(battle.participant_for(user), ActionType.MOVE, battle.participant_for(target),
                    move, pokemon=user, target_pokemon=target)
    battle.use_move(action)
    return move


@pytest.mark.parametrize("retaliation,attack,multiplier", [
    ("Counter", "Tackle", 2), ("Mirror Coat", "Water Gun", 2),
    ("Metal Burst", "Tackle", 1.5), ("Metal Burst", "Water Gun", 1.5),
    ("Comeuppance", "Tackle", 1.5), ("Comeuppance", "Water Gun", 1.5),
])
def test_retaliation_returns_the_correct_multiple_of_a_current_opposing_hit(retaliation, attack, multiplier):
    battle, user, foe = build_battle()
    battle.rng = random.Random(0)
    battle.start_turn()
    use(battle, foe, user, attack)
    damage = user.max_hp - user.hp
    before = foe.hp
    move = use(battle, user, foe, retaliation)
    assert damage > 0
    assert before - foe.hp == int(damage * multiplier)
    assert move.pp == 9


@pytest.mark.parametrize("retaliation,attack", [("Counter", "Water Gun"), ("Mirror Coat", "Tackle")])
def test_counter_category_mismatch_remains_a_valid_failure(retaliation, attack):
    battle, user, foe = build_battle()
    battle.rng = random.Random(0)
    battle.start_turn()
    use(battle, foe, user, attack)
    before = foe.hp
    move = use(battle, user, foe, retaliation)
    assert foe.hp == before
    assert move.pp == 9


@pytest.mark.parametrize("name", ["Counter", "Mirror Coat", "Metal Burst", "Comeuppance"])
def test_missing_or_previous_turn_damage_does_not_enable_retaliation(name):
    battle, user, foe = build_battle()
    battle.rng = random.Random(0)
    battle.start_turn()
    use(battle, user, foe, name)
    assert foe.hp == foe.max_hp
    use(battle, foe, user, "Tackle")
    battle.end_turn()
    battle.start_turn()
    before = foe.hp
    use(battle, user, foe, name)
    assert foe.hp == before


def test_counter_retargets_the_opponent_who_actually_dealt_the_hit():
    battle, user, hitter = build_battle()
    other = load_modules()["Pokemon"]("Other", level=50, hp=200, max_hp=200)
    other.base_stats = make_stats()
    other.types = ["Normal"]
    part = battle.participant_for(hitter)
    part.max_active = 2
    part.pokemons.append(other)
    part.active.append(other)
    other.battle, other.side = battle, part.side
    battle.rng = random.Random(0)
    battle.start_turn()
    use(battle, hitter, user, "Tackle")
    damage = user.max_hp - user.hp
    use(battle, user, other, "Counter")
    assert hitter.max_hp - hitter.hp == damage * 2
    assert other.hp == other.max_hp


def test_counter_preserves_type_immunity_as_a_valid_failure():
    battle, user, foe = build_battle(defender_types=["Ghost"])
    battle.start_turn()
    use(battle, foe, user, "Tackle")
    assert user.hp < user.max_hp
    move = use(battle, user, foe, "Counter")
    assert foe.hp == foe.max_hp
    assert move.pp == 9


def test_later_allied_damage_does_not_replace_the_last_opposing_hit():
    battle, user, foe = build_battle()
    ally = load_modules()["Pokemon"]("Ally", level=50, hp=200, max_hp=200)
    ally.base_stats = make_stats()
    ally.types = ["Normal"]
    part = battle.participant_for(user)
    part.max_active = 2
    part.pokemons.append(ally)
    part.active.append(ally)
    ally.battle, ally.side = battle, part.side
    battle.rng = random.Random(0)
    battle.start_turn()
    use(battle, foe, user, "Tackle")
    opposing_damage = user.max_hp - user.hp
    use(battle, ally, user, "Water Gun")
    use(battle, user, foe, "Counter")
    assert foe.max_hp - foe.hp == opposing_damage * 2


def test_counter_hits_the_replacement_in_the_original_attacking_slot():
    battle, user, foe = build_battle()
    reserve = load_modules()["Pokemon"]("Reserve", level=50, hp=200, max_hp=200)
    reserve.base_stats = make_stats()
    reserve.types = ["Normal"]
    part = battle.participant_for(foe)
    part.pokemons.append(reserve)
    reserve.battle, reserve.side = battle, part.side
    battle.start_turn()
    use(battle, foe, user, "Tackle")
    damage = user.max_hp - user.hp
    battle.switch_pokemon(part, reserve)
    before = foe.hp
    use(battle, user, reserve, "Counter")
    assert reserve.max_hp - reserve.hp == damage * 2
    assert foe.hp == before
