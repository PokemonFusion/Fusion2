"""Move summaries distinguish successful conditions from blocked effects."""

import random

import pytest

from pokemon.battle._shared import _normalize_key, get_raw
from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import MOVEDEX, Action, ActionType, Battle, BattleMove, BattleParticipant, BattleType


@pytest.mark.parametrize("types,initial,ability,applied", [
    (["Normal"], 0, "", True),
    (["Normal"], "par", "", False),
    (["Electric"], 0, "", False),
    (["Normal"], 0, "Limber", False),
])
def test_thunder_wave_summary_matches_actual_status(types, initial, ability, applied):
    """Successful paralysis has a success summary; blocked paralysis does not."""
    user = Pokemon("Raichu", level=5, hp=20, max_hp=20)
    target = Pokemon("Target", level=5, hp=20, max_hp=20, types=types, ability=ability, status=initial)
    actor, foe = BattleParticipant("Player", [user]), BattleParticipant("Foe", [target])
    actor.active, foe.active = [user], [target]
    battle = Battle(BattleType.WILD, [actor, foe])
    battle.rng = random.Random(1)  # This summary case requires a qualifying hit.
    messages = []
    battle.log_action = messages.append
    move = BattleMove("Thunder Wave", accuracy=True, pp=20, raw={
        "category": "Status", "type": "Electric", "status": "par", "target": "normal",
    })
    battle.use_move(Action(actor, ActionType.MOVE, foe, move, pokemon=user))
    if applied:
        assert target.status == "par"
        assert "Raichu used Thunder Wave on Target!" in messages
        assert not any("had no effect" in message for message in messages)
    else:
        assert target.status == initial
        assert any("had no effect" in message for message in messages)
    assert move.pp == 19


def test_thunder_wave_miss_keeps_status_empty_and_spends_one_pp():
    """A normal accuracy failure must never announce successful paralysis."""
    user = Pokemon("Raichu", level=5, hp=20, max_hp=20)
    target = Pokemon("Target", level=5, hp=20, max_hp=20, types=["Normal"])
    actor, foe = BattleParticipant("Player", [user]), BattleParticipant("Foe", [target])
    actor.active, foe.active = [user], [target]
    battle = Battle(BattleType.WILD, [actor, foe])
    battle.rng = random.Random(2)
    messages = []
    battle.log_action = messages.append
    move = BattleMove("Thunder Wave", pp=20)
    battle.use_move(Action(actor, ActionType.MOVE, foe, move, pokemon=user))
    assert not target.status and move.pp == 19
    assert any("missed" in message for message in messages)
    assert "Raichu used Thunder Wave on Target!" not in messages


@pytest.mark.parametrize("first_stage,second_stage", [(0, 0), (-6, 0), (0, -6), (-6, -6)])
def test_growl_reports_each_spread_target_and_its_actual_stat_change(first_stage, second_stage):
    """Both foes get accurate summaries, including independently capped stats."""
    user = Pokemon("Growler", level=5, hp=20, max_hp=20)
    ally = Pokemon("Ally", level=5, hp=20, max_hp=20)
    first = Pokemon("First Foe", level=5, hp=20, max_hp=20)
    second = Pokemon("Second Foe", level=5, hp=20, max_hp=20)
    first.boosts["attack"], second.boosts["attack"] = first_stage, second_stage
    actor, foe = BattleParticipant("Player", [user, ally]), BattleParticipant("Foe", [first, second])
    actor.active, foe.active = [user, ally], [first, second]
    battle = Battle(BattleType.PVP, [actor, foe])
    messages = []
    battle.log_action = messages.append
    move = BattleMove("Growl", accuracy=True, pp=40, raw={
        "category": "Status", "type": "Normal", "boosts": {"atk": -1}, "target": "allAdjacentFoes",
    })
    battle.use_move(Action(actor, ActionType.MOVE, foe, move, pokemon=user, target_pokemon=first))
    for target, initial in ((first, first_stage), (second, second_stage)):
        assert target.boosts["attack"] == max(-6, initial-1)
        if initial > -6:
            assert messages.count(f"Growler used Growl on {target.name}!") == 1
            assert any(target.name in message and "Attack fell" in message for message in messages)
        else:
            assert f"Growler's Growl failed to affect {target.name}'s stats!" in messages
    assert ally.boosts.get("attack", 0) == 0
    assert user.boosts.get("attack", 0) == 0
    assert move.pp == 39


@pytest.mark.parametrize("name,volatile", [
    ("Life Dew", None), ("Teeter Dance", "confusion"),
    ("Heal Block", "healblock"), ("Corrosive Gas", None),
])
@pytest.mark.parametrize("applied", [True, False])
def test_spread_nonstat_effects_match_messages(name, volatile, applied):
    """Production move callbacks cannot contradict healing, conditions or item loss."""
    user = Pokemon("Supporter", level=5, hp=10 if applied else 20, max_hp=20)
    ally = Pokemon("Friend", level=5, hp=10 if applied else 20, max_hp=20)
    first = Pokemon("First Foe", level=5, hp=20, max_hp=20)
    second = Pokemon("Second Foe", level=5, hp=20, max_hp=20)
    actor, foe = BattleParticipant("Player", [user, ally]), BattleParticipant("Foe", [first, second])
    actor.active, foe.active = [user, ally], [first, second]
    battle = Battle(BattleType.PVP, [actor, foe])
    messages = []
    battle.log_action = messages.append
    targets = [user, ally] if name == "Life Dew" else ([first, second] if name == "Heal Block" else [first, second, ally])
    for target in targets:
        if volatile and not applied:
            target.volatiles[volatile] = True
        if name == "Corrosive Gas" and applied:
            target.item = "Leftovers"
    raw = get_raw(MOVEDEX[_normalize_key(name)])
    move = BattleMove(name, raw=raw, accuracy=True, pp=raw["pp"])
    target = targets[0]
    battle.use_move(Action(actor, ActionType.MOVE, actor if target is user else foe,
                           move, pokemon=user, target_pokemon=target))
    for target in targets:
        if name == "Life Dew":
            assert target.hp == (15 if applied else 20)
        elif volatile:
            assert volatile in target.volatiles
        else:
            assert not target.item and not getattr(target, "held_item", None)
        success = f"Supporter used {name}!" if target is user else f"Supporter used {name} on {target.name}!"
        if applied:
            assert messages.count(success) == 1
        else:
            assert success not in messages
    if applied:
        assert not any("had no effect" in message for message in messages), messages
    else:
        assert any("had no effect" in message for message in messages), messages
    assert move.pp == raw["pp"]-1


@pytest.mark.parametrize("initial,remaining", [
    (True, 4), ({}, 4), ({"turns": 3}, 2), ({"turns": 0}, None),
])
def test_confusion_advances_legacy_and_initialized_state(monkeypatch, initial, remaining):
    """Old confusion checkpoints recover without resetting an existing countdown."""
    from pokemon.dex.functions import conditions_funcs

    monkeypatch.setattr(conditions_funcs.random, "randint", lambda low, high: 5)
    monkeypatch.setattr(conditions_funcs.random, "random", lambda: 1.0)
    pokemon = Pokemon("Confused Friend", level=5, hp=20, max_hp=20)
    pokemon.volatiles["confusion"] = initial
    assert conditions_funcs.Confusion().onBeforeMove(pokemon) is True
    if remaining is None:
        assert "confusion" not in pokemon.volatiles
    else:
        assert pokemon.volatiles["confusion"]["turns"] == remaining


def test_confusion_countdown_advances_once_per_executed_action(monkeypatch):
    """The turn dispatcher and move executor must share one prevention check."""
    from pokemon.dex.functions import conditions_funcs

    monkeypatch.setattr(conditions_funcs.random, "random", lambda: 1.0)
    user = Pokemon("Squirtle", level=5, hp=20, max_hp=20)
    target = Pokemon("Eevee", level=5, hp=20, max_hp=20)
    user.volatiles["confusion"] = {"turns": 4}
    actor, foe = BattleParticipant("Player", [user]), BattleParticipant("Foe", [target])
    battle = Battle(BattleType.PVP, [actor, foe])
    move = BattleMove("Tackle", pp=10)
    battle.execute_actions([Action(actor, ActionType.MOVE, foe, move, pokemon=user)])
    assert user.volatiles["confusion"]["turns"] == 3
    assert move.pp == 9
