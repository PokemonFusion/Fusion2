"""A form's first-hit defense must be consumed and respect legal immunities."""

import random

import pytest

from .helpers import build_battle, load_modules


def carrier(species, ability, types):
    """Prepare a real named ability and its original form inside the engine."""
    from pokemon.battle.engine import _resolve_ability

    battle, user, holder = build_battle(defender_ability=ability, defender_types=types)
    holder.name = holder.species = holder.base_species = species
    battle.singleEvent("Start", _resolve_ability(ability), holder.ability_state, holder)
    return battle, user, holder


def strike(battle, user, holder, name):
    """Resolve a real player-style action with a repeatable hit roll."""
    from pokemon.battle.actions import Action, ActionType

    battle.rng = random.Random(0)
    action = Action(battle.participant_for(user), ActionType.MOVE,
                    battle.participant_for(holder), load_modules()["BattleMove"](name), pokemon=user)
    battle.use_move(action)
    assert not getattr(battle, "_callback_failures", [])


def test_disguise_breaks_once_costs_one_eighth_hp_and_allows_the_next_hit():
    battle, user, holder = carrier("Mimikyu", "Disguise", ["Ghost", "Fairy"])
    strike(battle, user, holder, "Shadow Ball")
    assert holder.hp == holder.max_hp - holder.max_hp // 8
    assert str(holder.species) == "Mimikyu-Busted"
    before = holder.hp
    strike(battle, user, holder, "Shadow Ball")
    assert holder.hp < before


def test_a_natural_type_immunity_does_not_consume_disguise():
    battle, user, holder = carrier("Mimikyu", "Disguise", ["Ghost", "Fairy"])
    strike(battle, user, holder, "Tackle")
    assert holder.hp == holder.max_hp
    assert str(holder.species) == "Mimikyu"


def test_substitute_takes_the_hit_without_consuming_disguise():
    battle, user, holder = carrier("Mimikyu", "Disguise", ["Ghost", "Fairy"])
    holder.volatiles["substitute"] = {"hp": 100}
    strike(battle, user, holder, "Shadow Ball")
    assert "substitute" not in holder.volatiles or holder.volatiles["substitute"]["hp"] < 100
    assert holder.hp == holder.max_hp
    assert str(holder.species) == "Mimikyu"


def test_ice_face_changes_once_without_chip_and_allows_the_next_physical_hit():
    battle, user, holder = carrier("Eiscue", "Ice Face", ["Ice"])
    strike(battle, user, holder, "Tackle")
    assert holder.hp == holder.max_hp
    assert str(holder.species) == "Eiscue-Noice"
    strike(battle, user, holder, "Tackle")
    assert holder.hp < holder.max_hp
    assert str(holder.species) == "Eiscue-Noice"


@pytest.mark.parametrize("species", ["Eiscue", "Eiscue-Noice"])
def test_ice_face_does_not_block_special_damage(species):
    battle, user, holder = carrier(species, "Ice Face", ["Ice"])
    strike(battle, user, holder, "Water Gun")
    assert holder.hp < holder.max_hp
    assert str(holder.species) == species


def test_ice_face_does_not_prevent_a_guaranteed_special_critical():
    import copy

    from pokemon.dex import MOVEDEX

    battle, user, holder = carrier("Eiscue", "Ice Face", ["Ice"])
    move = copy.deepcopy(MOVEDEX["frostbreath"])
    result = load_modules()["damage_calc"](user, holder, move, battle=battle, rng=random.Random(0))
    assert result.debug["critical"] == [True]


def test_an_initial_noice_form_does_not_get_an_extra_free_block():
    battle, user, holder = carrier("Eiscue-Noice", "Ice Face", ["Ice"])
    strike(battle, user, holder, "Tackle")
    assert holder.hp < holder.max_hp
    assert str(holder.species) == "Eiscue-Noice"
