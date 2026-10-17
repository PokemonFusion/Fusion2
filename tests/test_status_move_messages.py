"""Move summaries distinguish successful conditions from blocked effects."""

import pytest

from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import Action, ActionType, Battle, BattleMove, BattleParticipant, BattleType


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
