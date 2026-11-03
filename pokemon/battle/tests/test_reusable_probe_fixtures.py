"""Run reusable fixture definitions through native entry, actions and residuals."""

import random
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from .helpers import load_modules
from .test_diagnosed_item_effects import native_battle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "qa"))
from tools.qa.live_dex_ability_probes import TRIGGERS, fixtures
from tools.qa.live_dex_cases import move_cases
from tools.qa.live_smoke_effects_cases import probes


def run_case(case):
    """Execute the generated singles commands with real dex moves and items."""
    from pokemon import dex
    from pokemon.battle.actions import Action, ActionType
    from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats
    from pokemon.names import resolve_dex_entry

    modules = load_modules()
    user, target = case.a[0], case.b[0]
    battle, holder, foe = native_battle(
        user.species, user.item, target.species,
        hp_fraction=user.hp_fraction, ability=user.ability,
    )
    foe.ability = target.ability
    for mon, spec in ((holder, user), (foe, target)):
        if mon.level != spec.level:
            mon.level = spec.level
            calculated = SimpleNamespace(species=spec.species, level=spec.level,
                                         ivs=[0] * 6, evs=[0] * 6, nature="Hardy")
            mon.base_stats = modules["Stats"](**get_stats(calculated))
            mon.max_hp = get_max_hp(calculated)
            mon.hp = max(1, int(mon.max_hp * spec.hp_fraction))
        mon.moves = [modules["BattleMove"](name=name) for name in spec.moves]
        assert all(resolve_dex_entry(dex.MOVEDEX, name) for name in spec.moves)
        battle.on_enter_battle(mon)
    initial = (holder.item, holder.hp, foe.status)
    battle.rng = random.Random(case.seed)
    for commands in case.turns:
        actions = []
        for side, command in commands:
            source, recipient = (holder, foe) if side == "a" else (foe, holder)
            name = command.removeprefix("+attack ")
            actions.append(Action(
                battle.participant_for(source), ActionType.MOVE,
                battle.participant_for(recipient),
                move=next(move for move in source.moves if move.name == name), pokemon=source,
            ))
        battle.execute_turn(actions)
    assert not getattr(battle, "_callback_failures", [])
    return battle, holder, foe, initial


@pytest.mark.parametrize("source", ["catalog", "effects"])
def test_recycle_restores_a_naturally_consumed_berry_and_retains_it(source):
    from pokemon import dex

    case = (next(case for case in move_cases(dex) if case.subject == "Recycle")
            if source == "catalog" else next(probe for probe in probes() if probe.subject == "Recycle").cases[0])
    _, holder, _, initial = run_case(case)
    assert not initial[0] and initial[1] > holder.max_hp / 2
    assert holder.item.raw["name"] == "Oran Berry"
    assert holder.hp == initial[1]


def test_low_hp_recycle_can_legally_consume_the_restored_berry_again():
    case = next(probe for probe in probes() if probe.subject == "Recycle").cases[0]
    case = replace(case, a=(replace(case.a[0], hp_fraction=.2),))
    _, holder, _, initial = run_case(case)
    assert not initial[0] and initial[1] <= holder.max_hp / 2
    assert not holder.item
    assert holder.hp == initial[1] + 10


@pytest.mark.parametrize("trigger", [t for t in TRIGGERS if t.ability == "Mycelium Might"],
                         ids=lambda t: t.label)
def test_mycelium_status_pairs_retain_real_bypass_and_cure_controls(trigger):
    assert trigger.positive_trigger == (trigger.label == "status-through-good-as-gold")
    control, actual = fixtures(trigger)
    for case in (control, actual):
        battle, _, foe, initial = run_case(case)
        assert not initial[2]
        expected = case.assertions[-1]
        assert (foe.status == "par") == (expected["type"] == "status")
        if trigger.label == "limber-cure-negative" and case is actual:
            # The earlier single-move test observes temporary bypass. The
            # reusable pair asserts the completed turn, including legal cure.
            assert foe.ability == "Limber"
            battle.residual()
            assert not foe.status
