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
