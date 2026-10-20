"""Verify sacrifice and revival preconditions against actual battle actions."""

import logging
import random
from types import SimpleNamespace

import pytest

from .helpers import build_battle, load_modules


@pytest.fixture(autouse=True)
def quiet_battle_log():
    """Keep offline events out of live acceptance logs."""
    logger = logging.getLogger("battle")
    previous = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = previous


def use(battle, user, target, name):
    """Use a real named move without bypassing prevention or PP hooks."""
    from pokemon.battle.actions import Action, ActionType

    battle.rng = random.Random(0)
    battle.use_move(Action(battle.participant_for(user), ActionType.MOVE,
                           battle.participant_for(target), load_modules()["BattleMove"](name), pokemon=user))
    assert not getattr(battle, "_callback_failures", [])


def reserve(battle, user, hp=50):
    """Add a separate prepared reserve with a real battle side and HP state."""
    mon = load_modules()["Pokemon"]("Eevee", hp=hp, max_hp=200)
    mon.battle = battle
    part = battle.participant_for(user)
    part.pokemons.append(mon)
    mon.side = part.side
    return mon


@pytest.mark.parametrize("name,condition", [("Healing Wish", "healingwish"), ("Lunar Dance", "lunardance")])
def test_sacrifice_faints_its_user_and_retains_the_replacement_slot_effect(name, condition):
    battle, user, target = build_battle()
    reserve(battle, user)
    use(battle, user, user, name)
    assert user.hp == 0
    assert condition in user.side.slot_conditions[0]


@pytest.mark.parametrize("name", ["Healing Wish", "Lunar Dance"])
def test_sacrifice_without_a_living_reserve_fails_without_killing_its_user(name):
    battle, user, target = build_battle()
    reserve(battle, user, hp=0)
    use(battle, user, user, name)
    assert user.hp == user.max_hp
    assert not user.side.slot_conditions


def test_memento_faints_its_user_only_after_successfully_lowering_the_target():
    battle, user, target = build_battle()
    use(battle, user, target, "Memento")
    assert user.hp == 0
    assert target.boosts.get("attack", target.boosts.get("atk")) == -2


def test_memento_fails_against_protect_without_sacrificing():
    battle, user, target = build_battle()
    use(battle, target, target, "Protect")
    use(battle, user, target, "Memento")
    assert user.hp == user.max_hp


def test_revival_restores_one_fainted_reserve_without_switching_its_user():
    battle, user, target = build_battle()
    fainted = reserve(battle, user, hp=0)
    fainted.is_fainted = True
    use(battle, user, user, "Revival Blessing")
    assert fainted.hp == fainted.max_hp // 2 and not fainted.is_fainted
    assert battle.participant_for(user).active == [user]
    assert not user.tempvals.get("switch_out")


def test_revival_fails_when_the_only_reserve_is_alive():
    battle, user, target = build_battle()
    living = reserve(battle, user, hp=50)
    use(battle, user, user, "Revival Blessing")
    assert living.hp == 50 and not user.tempvals.get("switch_out")


class OwnedPP:
    """Independent owned PP capacity and persistence for a replacement."""

    def __init__(self, remaining, capacity=37):
        self.saved = []
        self.slot = SimpleNamespace(move=SimpleNamespace(name="Tackle"), current_pp=remaining,
                                    pokemon=SimpleNamespace(get_max_pp=lambda name: capacity))
        self.slot.save = lambda **kwargs: self.saved.append(self.slot.current_pp)

    def all(self):
        """Return the independently saved active slot."""
        return [self.slot]


def test_lunar_dance_restores_owned_and_runtime_pp_even_on_a_healthy_replacement():
    battle, user, target = build_battle()
    replacement = reserve(battle, user, hp=200)
    slot = replacement.activemoveslot_set = OwnedPP(3)
    cached = load_modules()["Move"]("Tackle")
    cached.pp = 3
    replacement.moves = [cached]
    battle.add_slot_condition(user, "lunardance", {}, source=user)
    part = battle.participant_for(user)
    part.active = [replacement]
    part.side.active = part.active
    battle._run_slot_swap_events(replacement)
    assert slot.slot.current_pp == cached.pp == 37
    assert slot.saved == [37]
    assert not part.side.slot_conditions


def test_healing_wish_does_not_restore_pp_and_waits_for_an_injured_replacement():
    battle, user, target = build_battle()
    replacement = reserve(battle, user, hp=200)
    slot = replacement.activemoveslot_set = OwnedPP(3)
    battle.add_slot_condition(user, "healingwish", {}, source=user)
    part = battle.participant_for(user)
    part.active = [replacement]
    part.side.active = part.active
    battle._run_slot_swap_events(replacement)
    assert slot.slot.current_pp == 3 and not slot.saved
    assert "healingwish" in part.side.slot_conditions[0]


@pytest.mark.parametrize("name", ["Healing Wish", "Lunar Dance"])
def test_the_actual_faint_replacement_path_consumes_the_healing_slot(name):
    battle, user, target = build_battle()
    battle.award_xp = battle.award_txp = False
    replacement = reserve(battle, user)
    replacement.status = "psn"
    use(battle, user, user, name)
    battle.run_faint()
    assert battle.participant_for(replacement).active == [replacement]
    assert replacement.hp == replacement.max_hp and not replacement.status
    assert not replacement.side.slot_conditions


def test_full_pp_does_not_cause_writes_or_consume_a_lunar_dance_slot():
    battle, user, target = build_battle()
    replacement = reserve(battle, user, hp=200)
    slots = replacement.activemoveslot_set = OwnedPP(37)
    battle.add_slot_condition(user, "lunardance", {}, source=user)
    part = battle.participant_for(user)
    part.active = [replacement]
    part.side.active = part.active
    battle._run_slot_swap_events(replacement)
    assert slots.slot.current_pp == 37 and not slots.saved
    assert "lunardance" in part.side.slot_conditions[0]
