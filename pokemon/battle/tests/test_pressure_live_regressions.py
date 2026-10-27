"""Pressure scope regressions diagnosed using fresh real-login QA battles."""

import pytest

from .helpers import build_battle, load_modules, make_stats


def use(battle, user, target, name="Tackle", pp=10):
    """Use the actual dex move through normal action resolution."""
    from pokemon.battle.actions import Action, ActionType

    move = load_modules()["BattleMove"](name, pp=pp)
    user.moves = [move]
    action = Action(battle.participant_for(user), ActionType.MOVE,
                    battle.participant_for(target), move, pokemon=user)
    battle.use_move(action)
    return move


def test_pressure_holder_does_not_pay_its_own_surcharge():
    battle, holder, opponent = build_battle(attacker_ability="Pressure")
    move = use(battle, holder, opponent)
    assert move.pp == 9


def test_opponent_targeting_pressure_holder_spends_two_pp():
    battle, user, holder = build_battle(defender_ability="Pressure")
    move = use(battle, user, holder)
    assert move.pp == 8


@pytest.mark.parametrize("name", ["Swords Dance", "Recover", "Splash"])
def test_self_targeted_move_ignores_pressure_on_both_sides(name):
    battle, user, holder = build_battle(attacker_ability="Pressure", defender_ability="Pressure")
    user.hp = 50
    move = use(battle, user, holder, name)
    assert move.pp == 9


def test_protected_pressure_holder_still_charges_extra_pp():
    battle, user, holder = build_battle(defender_ability="Pressure")
    holder.volatiles["protect"] = True
    move = use(battle, user, holder)
    assert move.pp == 8
    assert holder.hp == holder.max_hp


def test_two_turn_move_spends_pressure_cost_once_for_both_phases():
    battle, user, holder = build_battle(defender_ability="Pressure")
    battle.start_turn()
    move = use(battle, user, holder, "Fly")
    assert move.pp == 8
    battle.end_turn()
    battle.start_turn()
    release = use(battle, user, holder, "Fly", pp=move.pp)
    assert release.pp == 8


def test_suppressed_pressure_does_not_add_cost():
    battle, user, holder = build_battle(defender_ability="Pressure")
    holder.volatiles["gastroacid"] = True
    move = use(battle, user, holder)
    assert move.pp == 9


def test_spread_move_charges_each_opposing_pressure_holder_once():
    battle, user, holder = build_battle(defender_ability="Pressure")
    second = load_modules()["Pokemon"]("Second", level=50, hp=200, max_hp=200)
    second.base_stats = make_stats()
    second.types = ["Normal"]
    second.ability = "Pressure"
    opponent = battle.participant_for(holder)
    opponent.pokemons.append(second)
    opponent.active.append(second)
    second.battle = battle
    second.side = opponent.side
    move = use(battle, user, holder, "Surf")
    assert move.pp == 7


def test_side_target_without_mustpressure_does_not_charge_pressure():
    battle, user, holder = build_battle(defender_ability="Pressure")
    move = load_modules()["BattleMove"]("Side Effect", pp=10, raw={"target": "foeSide"})
    battle.deduct_pp(user, move, target=holder)
    assert move.pp == 9


def test_mustpressure_flag_charges_opponents_for_a_self_targeted_move():
    battle, user, holder = build_battle(defender_ability="Pressure")
    move = use(battle, user, holder, "Imprison")
    assert move.raw["flags"]["mustpressure"]
    assert move.pp == 8
