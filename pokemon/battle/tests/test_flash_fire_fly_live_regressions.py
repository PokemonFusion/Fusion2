"""Regressions for the lifecycle failures observed by logged-in QA players."""

import random

import pytest

from .helpers import build_battle, load_modules


def use(battle, user, target, name, **kwargs):
    """Use a real dex move through the same engine entry as player choices."""
    from pokemon.battle.actions import Action, ActionType

    move = load_modules()["BattleMove"](name, **kwargs)
    action = Action(battle.participant_for(user), ActionType.MOVE,
                    battle.participant_for(target), move, pokemon=user)
    battle.use_move(action)
    return move


def test_flash_fire_remains_armed_after_end_of_turn_and_boosts_fire():
    battle, attacker, holder = build_battle(defender_ability="Flash Fire")
    battle.rng = random.Random(0)
    battle.start_turn()
    use(battle, attacker, holder, "Ember")
    assert holder.hp == holder.max_hp
    assert holder.ability_state["flashfire"] is True

    battle.end_turn()
    battle.start_turn()

    assert holder.ability_state["flashfire"] is True
    from pokemon.battle.engine import _resolve_ability

    fire_move = load_modules()["BattleMove"]("Ember", type="Fire")
    assert _resolve_ability(holder.ability).call("onModifySpA", 100, holder, attacker, fire_move) == 150


def test_flash_fire_expires_on_switch_out_instead_of_on_residual():
    battle, attacker, holder = build_battle(defender_ability="Flash Fire")
    battle.start_turn()
    use(battle, attacker, holder, "Ember")
    assert holder.ability_state["flashfire"] is True

    battle.on_switch_out(holder)

    assert holder.ability_state["flashfire"] is False


def test_non_fire_attack_does_not_arm_flash_fire():
    battle, attacker, holder = build_battle(defender_ability="Flash Fire")
    battle.rng = random.Random(0)
    battle.start_turn()
    use(battle, attacker, holder, "Tackle")
    battle.end_turn()
    assert holder.hp < holder.max_hp
    assert not holder.ability_state.get("flashfire")
    from pokemon.battle.engine import _resolve_ability

    fire_move = load_modules()["BattleMove"]("Ember", type="Fire")
    assert _resolve_ability(holder.ability).call("onModifySpA", 100, holder, attacker, fire_move) is None


def test_flash_fire_increases_real_fire_damage_after_a_complete_turn():
    from pokemon.battle.engine import _resolve_ability

    battle, attacker, holder = build_battle(defender_ability="Flash Fire")
    holder.ability = _resolve_ability(holder.ability)
    battle.rng = random.Random(0)
    battle.start_turn()
    use(battle, attacker, holder, "Ember")
    battle.end_turn()
    battle.start_turn()
    before = attacker.hp
    battle.rng = random.Random(0)
    use(battle, holder, attacker, "Ember")
    boosted = before - attacker.hp

    holder.ability_state["flashfire"] = False
    attacker.hp = before
    battle.rng = random.Random(0)
    use(battle, holder, attacker, "Ember")

    assert boosted > before - attacker.hp > 0


@pytest.mark.parametrize("name, volatile", [("Fly", "fly"), ("Dig", "dig")])
def test_two_turn_move_charges_once_strikes_then_clears(name, volatile):
    battle, user, target = build_battle()
    battle.rng = random.Random(0)
    messages = []
    battle.log_action = messages.append
    battle.start_turn()
    start = target.hp
    first = use(battle, user, target, name, pp=15)
    assert target.hp == start
    assert user.volatiles.get(volatile)
    assert first.pp == 14
    assert not any("failed" in message for message in messages)
    battle.end_turn()
    battle.start_turn()

    second = use(battle, user, target, name, pp=first.pp)

    assert target.hp < start
    assert volatile not in user.volatiles
    assert second.pp == 14


def test_fly_release_can_be_blocked_by_protect_without_restarting_charge():
    battle, user, target = build_battle()
    battle.start_turn()
    use(battle, user, target, "Fly")
    target.volatiles["protect"] = True
    battle.end_turn()
    battle.start_turn()

    use(battle, user, target, "Fly")

    assert target.hp == target.max_hp
    assert "fly" not in user.volatiles


def test_successful_try_move_callback_runs_once_per_use():
    battle, user, target = build_battle()
    calls = []

    def try_move(*args, **kwargs):
        calls.append(1)
        return True

    use(battle, user, target, "Tackle", onTryMove=try_move,
        raw={"onTryMove": try_move})

    assert calls == [1]
