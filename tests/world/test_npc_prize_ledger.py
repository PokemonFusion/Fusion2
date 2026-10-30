"""Corrupt and foreign outcome qualifications must never become money multipliers."""

from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
import pytest

from pokemon.battle.npc_prize_items import NPCPrizeItems


def fixture():
    """Keep this checkpoint-schema test independent from real owned-row acceptance."""
    ref, reward = "owned:" + str(uuid4()), str(uuid4())
    battle = SimpleNamespace(mechanic_battle_id=reward, mechanic_turn=2,
                             mechanic_controllers={ref: "42"})
    record = {"owner": "42", "pokemon": ref, "item": "amuletcoin", "phase": "entry", "turn": 0, "reward": reward}
    return battle, {"42": record}


@pytest.mark.parametrize("field,value", [("owner", "43"), ("pokemon", "owned:" + str(uuid4())),
    ("item", "leftovers"), ("phase", "final_gear"), ("turn", True), ("turn", -1),
    ("turn", 3), ("reward", str(uuid4()))])
def test_invalid_or_foreign_qualification_refuses_without_mutation(field, value):
    """Outcome, owner, native reference and participation timing are all bound."""
    battle, records = fixture()
    records["42"][field] = value
    original = deepcopy(records)
    with pytest.raises(ValueError):
        NPCPrizeItems.restore(battle, records)
    assert records == original


def test_old_empty_state_and_valid_detached_checkpoint():
    """Old battles earn no retroactive bonus, and copied evidence cannot mutate its original."""
    battle, records = fixture()
    NPCPrizeItems.restore(battle, {})
    assert NPCPrizeItems.freeze(battle) == {}
    NPCPrizeItems.restore(battle, records)
    detached = NPCPrizeItems.freeze(battle)
    detached["42"]["item"] = "luckincense"
    assert records["42"]["item"] == "amuletcoin"
    assert battle.npc_prize_qualifications["42"]["item"] == "amuletcoin"
