"""Known scripted-target moves remain selectable through shared legality."""

import pytest

from pokemon.battle.legal_actions import LegalActions

from .helpers import build_battle, load_modules


@pytest.mark.parametrize("name", ["Counter", "Mirror Coat", "Metal Burst", "Comeuppance"])
def test_scripted_moves_are_selectable_and_auto_target_the_living_foe(name):
    battle, user, foe = build_battle()
    move = load_modules()["Move"](name)
    move.pp = 10
    user.moves = [move]
    legal = LegalActions(battle, battle.participant_for(user), user)
    actions = legal.moves(fallback=False)
    assert len(actions) == 1
    assert actions[0].move.raw["target"] == "scripted"
    assert actions[0].target_pokemon is foe
    assert "scripted" in legal.automatic_targets


def test_scripted_targets_do_not_include_fainted_foes_or_bypass_pp():
    battle, user, foe = build_battle()
    move = load_modules()["Move"]("Counter")
    move.pp = 0
    user.moves = [move]
    legal = LegalActions(battle, battle.participant_for(user), user)
    assert legal.moves(fallback=False) == []
    foe.hp = 0
    assert legal.targets(load_modules()["BattleMove"]("Counter", raw={"target": "scripted"})) == []


def test_unknown_target_classes_are_still_rejected():
    battle, user, _ = build_battle()
    legal = LegalActions(battle, battle.participant_for(user), user)
    assert legal.targets(load_modules()["BattleMove"]("Invalid", raw={"target": "not-supported"})) == []
