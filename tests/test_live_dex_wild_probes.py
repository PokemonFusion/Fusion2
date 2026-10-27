"""Wild acceptance must use actual flee state and normal complete cleanup."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import live_dex_wild_probes as wild


def record():
    """Make an independently observed guaranteed escape with a deleted foe."""
    frame = {"type": "BattleType.WILD", "sides": {"A": {"active": [{"species": "Eevee"}]},
                                                   "B": {"active": [{"ability": "Arena Trap"}]}}}
    players = {label: {"ordinary": True, "battle_lock": False, "battle_id": None} for label in ("a", "b")}
    final = copy.deepcopy(frame) | {"flee_result": {"success": True, "reason": "runaway"}}
    return {"probe": {"species": "Eevee", "foe_ability": "Arena Trap", "escapes": True, "reason": "runaway"},
            "before": {"battle": frame, "players": players},
            "after": {"battle": None, "ended_battle": final, "players": players},
            "cleanup": {"battle": None, "room_battles": [], "staff_cleanup_required": False, "players": players},
            "encounter_deleted": True}


def test_saved_actual_flee_result_can_prove_guaranteed_escape():
    wild.evaluate(record())


def test_escape_text_without_actual_flee_state_does_not_pass():
    evidence = record()
    evidence["output"] = "You got away safely!"
    evidence["after"]["ended_battle"].pop("flee_result")
    with pytest.raises(AssertionError, match="Unexpected flee success"):
        wild.evaluate(evidence)


@pytest.mark.parametrize("failure", ["staff_cleanup_required", "encounter_deleted", "battle_lock"])
def test_incomplete_or_staff_cleanup_cannot_pass(failure):
    evidence = record()
    if failure == "encounter_deleted":
        evidence[failure] = False
    elif failure == "battle_lock":
        evidence["cleanup"]["players"]["a"][failure] = True
    else:
        evidence["cleanup"][failure] = True
    with pytest.raises(AssertionError):
        wild.evaluate(evidence)
