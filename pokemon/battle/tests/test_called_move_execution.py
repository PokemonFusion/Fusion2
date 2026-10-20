"""Called attacks must use the ordinary effect pipeline without extra owned PP."""

import logging
import random
from types import SimpleNamespace

import pytest

from .helpers import build_battle, load_modules


@pytest.fixture(autouse=True)
def quiet_log():
    logger = logging.getLogger("battle")
    old = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = old


def use(battle, user, target, name):
    from pokemon.battle.actions import Action, ActionType
    battle.rng = random.Random(1)
    move = load_modules()["BattleMove"](name, pp=10)
    battle.use_move(Action(battle.participant_for(user), ActionType.MOVE,
                           battle.participant_for(target), move, pokemon=user))
    assert not getattr(battle, "_callback_failures", [])
    return move


@pytest.mark.parametrize("name", ["Nature Power", "Metronome", "Assist", "Sleep Talk"])
def test_real_called_damage_spends_only_the_callers_pp(name):
    battle, user, target = build_battle()
    modules = load_modules()
    calling, learned = modules["Move"](name), modules["Move"]("Tackle")
    calling.pp = learned.pp = 10
    user.moves = [calling, learned] if name == "Sleep Talk" else [calling]
    reserve = modules["Pokemon"]("Reserve", level=50, hp=100, max_hp=100)
    reserve.moves = [learned]
    battle.participants[0].pokemons.append(reserve)
    if name == "Metronome":
        battle.metronome_pool = ["Tackle"]
    if name == "Sleep Talk":
        user.status = "slp"
        user.status_state = {"time": 4, "startTime": 4}
    use(battle, user, user if name != "Assist" else target, name)
    assert target.hp < target.max_hp and user.hp == user.max_hp
    assert calling.pp == 9 and learned.pp == 10
    assert len(getattr(battle, "called_moves", [])) == 1


def test_sleep_talk_cannot_call_itself_or_rest_and_fails_when_healthy():
    battle, user, target = build_battle()
    modules = load_modules()
    user.moves = [modules["Move"]("Sleep Talk"), modules["Move"]("Rest")]
    use(battle, user, target, "Sleep Talk")
    assert target.hp == target.max_hp and not getattr(battle, "called_moves", [])
    user.status = "slp"
    use(battle, user, target, "Sleep Talk")
    assert target.hp == target.max_hp and not getattr(battle, "called_moves", [])


def test_magic_bounce_reflects_the_actual_drop_without_spending_holder_pp():
    battle, user, target = build_battle(defender_ability="Magic Bounce")
    use(battle, user, target, "Growl")
    assert target.boosts.get("attack", target.boosts.get("atk", 0)) == 0
    assert user.boosts.get("attack", user.boosts.get("atk", 0)) == -1


def test_two_magic_bounce_holders_do_not_recurse_and_nonreflectable_status_passes():
    battle, user, target = build_battle(attacker_ability="Magic Bounce", defender_ability="Magic Bounce")
    use(battle, user, target, "Growl")
    assert user.boosts.get("attack", user.boosts.get("atk", 0)) == -1
    user.hp = 50
    use(battle, user, user, "Recover")
    assert user.hp == 150


def test_magic_coat_reflects_for_the_current_turn_then_expires():
    battle, user, target = build_battle()
    use(battle, target, target, "Magic Coat")
    use(battle, user, target, "Growl")
    assert user.boosts.get("attack", user.boosts.get("atk", 0)) == -1
    assert target.boosts.get("attack", target.boosts.get("atk", 0)) == 0
    battle.residual()
    use(battle, user, target, "Growl")
    assert target.boosts.get("attack", target.boosts.get("atk", 0)) == -1
