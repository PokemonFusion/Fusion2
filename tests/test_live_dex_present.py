"""Present's capped healing must be evidenced without hiding real failures."""

import json
from dataclasses import asdict, replace

import pytest

from tests.test_live_dex_runner import cases, observations, runner


def present_probe():
    """Declare the same isolated Present/Splash actions as the catalog."""
    return cases.DexCase(
        "move-present", "Present healing cap", (cases.Mon("Mew", ("Present",), "No Ability"),),
        (cases.Mon("Chansey", ("Splash",), "No Ability"),),
        (cases.turn("+attack Present"),), "dex", kind="move", subject="Present",
        raw={"type": "Normal", "category": "Physical", "accuracy": 90})


def capped_observations():
    """Supply independent branch, target, identity and owned PP observations."""
    states = observations("Present")
    for state in states:
        state["battle"]["id"] = 123
        for side, label in (("A", "a"), ("B", "b")):
            actor = runner.mon(state, side)
            actor["id"] = "owned:" + label
            if side == "B":
                actor.update(species="Chansey", types=["Normal"])
                state["players"][label]["pokemon"][0]["species"] = "Chansey"
    runner.mon(states[-1])["last_executed_move"] = {
        "name": "Present", "type": "Normal", "power": 0, "heal": .25}
    return states


MESSAGE = "Mew used Present on Chansey but it had no effect!"


def test_observed_present_full_hp_healing_cap_is_expected_not_positive_healing():
    result = runner.evaluate(present_probe(), capped_observations(), [MESSAGE, "Splash failed!"])
    assert result["status"] == "expected_failure"
    assert result["expected_healing_cap_verified"] is True
    assert result["positive_outcome_verified"] is False


def test_present_cap_is_identical_when_reassessing_the_saved_json_fixture():
    case = cases.from_dict(json.loads(json.dumps(asdict(present_probe()))))
    result = runner.evaluate(case, capped_observations(), [MESSAGE])
    assert result["expected_healing_cap_verified"] is True


@pytest.mark.parametrize("field,value", [
    ("name", "Tackle"), ("type", "Ghost"), ("power", 40), ("power", 80),
    ("power", 120), ("power", None), ("heal", None), ("heal", .5),
])
def test_wrong_or_missing_present_branch_cannot_explain_no_effect(field, value):
    states = capped_observations()
    runner.mon(states[-1])["last_executed_move"][field] = value
    assert runner.evaluate(present_probe(), states, [MESSAGE])["status"] == "needs_diagnosis"


def test_legacy_observation_cannot_infer_the_original_random_present_roll():
    states = capped_observations()
    runner.mon(states[-1])["last_executed_move"] = {"name": "Present", "type": "Normal"}
    assert runner.evaluate(present_probe(), states, [MESSAGE])["status"] == "needs_diagnosis"


@pytest.mark.parametrize("mutation", ["injured", "changed_max_hp", "wrong_target", "unbound_target",
                                     "item", "ability", "status", "protection", "weather", "extra_pp"])
def test_present_cap_requires_the_same_full_healthy_unblocked_target(mutation):
    states = capped_observations()
    target = runner.mon(states[-1], "B")
    if mutation == "injured":
        for state in states:
            runner.mon(state, "B")["hp"] = 50
    elif mutation == "changed_max_hp":
        target.update(hp=120, max_hp=120)
    elif mutation == "wrong_target":
        target["id"] = "owned:other"
    elif mutation == "unbound_target":
        states[-1]["players"]["b"]["pokemon"][0]["id"] = "other"
    elif mutation == "item":
        target["item"] = "Leftovers"
    elif mutation == "ability":
        target["ability"] = "Wonder Guard"
    elif mutation == "status":
        target["status"] = "par"
    elif mutation == "protection":
        target["volatiles"] = ["protect"]
    elif mutation == "weather":
        states[-1]["battle"]["field"]["weather"] = "Sandstorm"
    elif mutation == "extra_pp":
        states[-1]["players"]["a"]["pokemon"][0]["moves"][0]["current_pp"] -= 1
    assert runner.evaluate(present_probe(), states, [MESSAGE])["status"] == "needs_diagnosis"


@pytest.mark.parametrize("extra", ["Tackle failed!", "Present failed!", "Present doesn't affect Chansey!"])
def test_present_cap_cannot_hide_other_unexplained_failures(extra):
    assert runner.evaluate(present_probe(), capped_observations(), [MESSAGE, extra])["status"] == "needs_diagnosis"


@pytest.mark.parametrize("assertion", [{"type": "heal", "side": "B"}, {"type": "damage", "side": "B"}])
def test_expected_present_cap_cannot_satisfy_a_positive_effect_assertion(assertion):
    case = replace(present_probe(), assertions=(assertion,))
    with pytest.raises(AssertionError, match="outcome not observed"):
        runner.evaluate(case, capped_observations(), [MESSAGE])


def test_present_cap_cannot_explain_missing_pp_or_an_unresolved_turn():
    for field in ("pp", "turn"):
        states = capped_observations()
        if field == "pp":
            states[-1]["players"]["a"]["pokemon"][0]["moves"][0]["current_pp"] = 10
        else:
            states[-1]["battle"]["turn"] = states[0]["battle"]["turn"]
        with pytest.raises(AssertionError):
            runner.evaluate(present_probe(), states, [MESSAGE])


def test_present_cap_cannot_hide_callback_or_game_exceptions():
    states = capped_observations()
    states[-1]["battle"]["callback_failures"] = ["Present error"]
    with pytest.raises(AssertionError, match="callback exceptions"):
        runner.evaluate(present_probe(), states, [MESSAGE])
    with pytest.raises(AssertionError, match="reported an exception"):
        runner.evaluate(present_probe(), capped_observations(), [MESSAGE, "Unhandled error"])


@pytest.mark.parametrize("branch", ["heal", "damage"])
def test_actual_present_positive_effects_still_need_observed_hp_change(branch):
    states = capped_observations()
    if branch == "heal":
        runner.mon(states[0], "B")["hp"] = 50
        runner.mon(states[-1], "B")["hp"] = 75
    else:
        runner.mon(states[-1])["last_executed_move"].update(heal=None, power=80)
        runner.mon(states[-1], "B")["hp"] = 60
    case = replace(present_probe(), assertions=({"type": branch, "side": "B"},))
    result = runner.evaluate(case, states, ["Present resolved!"])
    assert result["status"] == "outcome_verified" and result["positive_outcome_verified"]


def test_other_move_or_other_actions_do_not_inherit_the_present_exception():
    for case in (replace(present_probe(), subject="Tackle"),
                 replace(present_probe(), turns=(cases.turn("+attack Present", "+attack Recover"),))):
        assert not runner.observed_present_healing_cap(case, capped_observations(), [MESSAGE])
