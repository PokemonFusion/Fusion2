"""Meaningful false-pass and inventory checks for the real-login dex sweep."""

import copy
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import live_dex_cases as cases
import live_dex_runner as runner


def test_code_fingerprint_ignores_constant_reference_counts():
    """Holding a returned constant cannot make unchanged loaded code look different."""
    from live_dex_server import code_fingerprint

    def sample():
        return ("Water", "Ground")

    before = code_fingerprint(sample.__code__)
    held = sample()
    assert code_fingerprint(sample.__code__) == before
    del held
    assert code_fingerprint(sample.__code__) == before


def test_code_fingerprint_detects_changed_nested_code_and_constants():
    """A stable digest must still distinguish real implementation changes."""
    from live_dex_server import code_fingerprint

    original = compile("def outer():\n def inner(): return 1\n return inner\n", "same.py", "exec")
    changed = compile("def outer():\n def inner(): return 2\n return inner\n", "same.py", "exec")
    assert code_fingerprint(original) != code_fingerprint(changed)


def observations(move="Tackle", spent=True, advanced=True):
    """Build independent observations with real-slot PP and ordinary accounts."""
    pokemon = {"species": "Mew", "hp": 100, "max_hp": 100, "types": ["Psychic"],
               "ability": "No Ability", "boosts": {}, "status": "", "ability_state": {},
               "moves": [{"move__name": move, "current_pp": 10}]}
    start = {"players": {side: {"ordinary": True, "pokemon": [copy.deepcopy(pokemon) | {"id": side}]} for side in ("a", "b")},
             "battle": {"turn": 1, "field": {}, "sides": {side: {"active": [copy.deepcopy(pokemon)]} for side in ("A", "B")}}}
    end = copy.deepcopy(start)
    end["battle"]["turn"] += int(advanced)
    end["players"]["a"]["pokemon"][0]["moves"][0]["current_pp"] -= int(spent)
    return [start, end]


def probe(**kwargs):
    """Declare one actual move probe independent of the generated catalog."""
    return cases.DexCase("move-tackle", "Tackle", (cases.Mon("Mew", ("Tackle",)),),
                         (cases.Mon("Mew", ("Splash",)),), (cases.turn("+attack Tackle"),), "dex",
                         kind="move", subject="Tackle", raw={"type": "Normal", "category": "Physical", "accuracy": 100}, **kwargs)


def test_sweep_covers_every_unique_local_catalog_entry():
    from pokemon import dex

    catalog = cases.catalog()
    assert len({case.key for case in catalog}) == len(catalog)
    for kind, entries in (("pokemon", dex.POKEDEX), ("move", dex.MOVEDEX), ("ability", dex.ABILITYDEX)):
        assert {cases.key(case.subject) for case in catalog if case.kind == kind} == {
            cases.key(entry.raw.get("name", entry.name)) for entry in entries.values()}


def test_a_completed_turn_without_pp_does_not_pass():
    with pytest.raises(AssertionError, match="did not spend PP"):
        runner.evaluate(probe(), observations(spent=False), ["Used Tackle!"])


def test_successful_sketch_follows_the_replaced_owned_slot():
    states = observations(move="Sketch")
    states[0]["players"]["a"]["pokemon"][0]["moves"][0]["current_pp"] = 1
    states[-1]["players"]["a"]["pokemon"][0]["moves"][0] = {"move__name": "Tackle", "current_pp": 35}
    case = replace(probe(), subject="Sketch", a=(cases.Mon("Smeargle", ("Sketch",)),),
                   assertions=({"type": "stored_move", "value": "Tackle"},))
    assert runner.evaluate(case, states, ["Sketch copied Tackle!"])["status"] == "outcome_verified"


def test_sketch_without_pp_or_an_actual_replacement_cannot_pass():
    states = observations(move="Sketch", spent=False)
    case = replace(probe(), subject="Sketch", a=(cases.Mon("Smeargle", ("Sketch",)),),
                   assertions=({"type": "stored_move", "value": "Tackle"},))
    with pytest.raises(AssertionError, match="did not spend PP"):
        runner.evaluate(case, states, ["Sketch copied Tackle!"])


def test_pp_spend_without_turn_completion_does_not_pass():
    with pytest.raises(AssertionError, match="complete turn"):
        runner.evaluate(probe(), observations(advanced=False), ["Used Tackle!"])


def test_damage_messages_cannot_prove_damage():
    case = probe(assertions=({"type": "damage", "side": "B"},))
    with pytest.raises(AssertionError, match="outcome not observed"):
        runner.evaluate(case, observations(), ["Tackle caused damage!"])


def test_smoke_is_not_reported_as_a_semantic_pass():
    result = runner.evaluate(probe(), observations(), ["Used Tackle!"])
    assert result["status"] == "smoke_completed"
    assert result["positive_outcome_verified"] is False


def test_actual_low_accuracy_miss_is_expected_but_not_positive_proof():
    case = replace(probe(), raw={"accuracy": 80}, assertions=({"type": "damage", "side": "B"},))
    result = runner.evaluate(case, observations(), ["Tackle missed!"])
    assert result["status"] == "expected_failure"
    assert result["positive_outcome_verified"] is False


def test_a_partial_multihit_miss_does_not_erase_observed_damage_and_spent_pp():
    case = replace(probe(), raw={"accuracy": 90}, assertions=({"type": "damage", "side": "B"},))
    states = observations()
    states[-1]["battle"]["sides"]["B"]["active"][0]["hp"] = 80
    result = runner.evaluate(case, states, ["Tackle hit once. Tackle missed its later hit!"])
    assert result["status"] == "outcome_verified"
    assert result["partial_or_explained_negative_observed"] is True


def test_an_unrelated_move_miss_cannot_explain_the_tested_moves_missing_damage():
    case = replace(probe(), raw={"accuracy": 90}, assertions=({"type": "damage", "side": "B"},))
    with pytest.raises(AssertionError, match="outcome not observed"):
        runner.evaluate(case, observations(), ["The opponent's Water Gun missed!"])


def test_transform_copy_text_without_correct_temporary_pp_cannot_pass():
    states = observations()
    states[-1]["battle"]["sides"]["A"]["active"][0]["runtime_moves"] = [{"name": "Tackle", "pp": 34}]
    case = probe(assertions=({"type": "runtime_move", "side": "A", "value": "Tackle", "pp": 5},))
    with pytest.raises(AssertionError, match="outcome not observed"):
        runner.evaluate(case, states, ["The move was copied!"])


def test_unexplained_failure_remains_a_diagnosis():
    result = runner.evaluate(probe(), observations(), ["Mew's Tackle failed!"])
    assert result["status"] == "needs_diagnosis"


def test_ordinary_opponents_splash_failure_does_not_taint_probe():
    result = runner.evaluate(probe(), observations(), ["Mew's Splash failed!"])
    assert result["status"] == "smoke_completed"


def test_unrecognized_assertion_cannot_silently_pass():
    with pytest.raises(AssertionError, match="Unknown outcome"):
        runner.evaluate(probe(assertions=({"type": "typo"},)), observations(), ["Used Tackle!"])


def test_swallowed_live_callback_exception_still_fails_the_probe():
    states = observations()
    states[-1]["battle"]["callback_failures"] = [{"error": "bad callback", "context": "run_event"}]
    with pytest.raises(AssertionError, match="callback exceptions"):
        runner.evaluate(probe(), states, ["Used Tackle!"])


def test_paired_damage_comparison_requires_actual_health_change():
    case = probe(assertions=({"type": "hp_loss_range", "side": "B", "minimum": 10},))
    with pytest.raises(AssertionError, match="outcome not observed"):
        runner.evaluate(case, observations(), ["Ability made the attack stronger!"])


def test_ended_battle_observation_keeps_live_final_damage_visible():
    states = observations()
    states[-1]["ended_battle"] = states[-1].pop("battle")
    states[-1]["battle"] = None
    states[-1]["ended_battle"]["sides"]["B"]["active"][0]["hp"] = 80
    states[-1]["ended_battle"]["sides"]["B"]["active"][0]["boosts"] = {"atk": -2}
    states[-1]["players"]["b"]["pokemon"][0]["hp"] = 80
    for side, part in states[-1]["ended_battle"]["sides"].items():
        part["active"][0]["id"] = "owned:" + side.lower()
        part["pokemon"] = copy.deepcopy(part["active"])
    result = runner.evaluate(probe(assertions=({"type": "damage", "side": "B"},
                                               {"type": "boosts", "side": "B", "values": {"atk": -2}})), states, ["Battle ended."])
    assert result["status"] == "outcome_verified"


def test_ended_battle_damage_cannot_hide_a_persistence_mismatch():
    states = observations()
    states[-1]["ended_battle"] = states[-1].pop("battle")
    states[-1]["battle"] = None
    states[-1]["players"]["b"]["pokemon"][0]["id"] = "qa"
    for side, part in states[-1]["ended_battle"]["sides"].items():
        part["pokemon"] = [{"id": "owned:qa", "hp": 80}] if side == "B" else []
    with pytest.raises(AssertionError, match="persisted owned HP"):
        runner.evaluate(probe(), states, ["Battle ended."])


def test_damage_follows_the_original_target_after_a_forced_switch():
    states = observations()
    states[0]["battle"]["sides"]["B"]["active"][0]["id"] = "owned:original"
    part = states[-1]["battle"]["sides"]["B"]
    original = copy.deepcopy(part["active"][0]) | {"id": "owned:original", "hp": 80}
    reserve = copy.deepcopy(part["active"][0]) | {"id": "owned:reserve", "hp": 200}
    part["active"] = [reserve]
    part["pokemon"] = [original, reserve]
    result = runner.evaluate(probe(assertions=({"type": "damage", "side": "B"},)), states, ["The damaged target was switched out."])
    assert result["status"] == "outcome_verified"


def test_a_substitute_message_without_actual_substitute_damage_does_not_pass():
    states = observations()
    states[-1]["battle"]["sides"]["A"]["active"][0]["volatile_state"] = {"substitute": {"hp": 25}}
    case = probe(assertions=({"type": "volatile_hp", "side": "A", "value": "substitute",
                             "minimum": 1, "below_fraction": [1, 4]},))
    with pytest.raises(AssertionError, match="outcome not observed"):
        runner.evaluate(case, states, ["The substitute took damage!"])


def test_pinned_case_round_trip_preserves_exact_fixture():
    from dataclasses import asdict

    case = probe()
    restored = cases.from_dict(asdict(case))
    assert asdict(restored) == asdict(case)


def test_replacement_pp_proof_reads_the_owned_reserve_and_exact_turn():
    states = observations()
    for state in states:
        state["players"]["a"]["pokemon"].append({"id": "reserve", "species": "Eevee", "hp": 100,
                                                 "stats": {"hp": 100}, "moves": [{"move__name": "Splash", "current_pp": 39}]})
    case = probe(assertions=({"type": "stored_pp", "side": "A", "index": 1, "move": "Splash", "value": 40},))
    with pytest.raises(AssertionError, match="outcome not observed"):
        runner.evaluate(case, states, ["Lunar Dance restored all PP!"])
    states[-1]["players"]["a"]["pokemon"][1]["moves"][0]["current_pp"] = 40
    assert runner.evaluate(case, states, [""])["status"] == "outcome_verified"


def test_species_entry_proof_does_not_require_identity_to_survive_a_later_ability_change():
    case = replace(probe(assertions=({"type": "species_identity"},)), kind="pokemon", subject="Mew",
                   raw={"types": ["Psychic"]})
    states = observations()
    states[-1]["battle"]["sides"]["A"]["active"][0]["types"] = ["Normal"]
    result = runner.evaluate(case, states, ["The native ability changed typing after the move."])
    assert result["status"] == "outcome_verified"


def test_ability_controls_change_only_the_subject_ability():
    from dataclasses import asdict

    import live_dex_ability_probes as probes

    identifiers = set()
    for trigger in probes.TRIGGERS:
        control, variant = probes.fixtures(trigger)
        assert variant.key not in identifiers
        identifiers.add(variant.key)
        left, right = asdict(control), asdict(variant)
        for name in ("key", "expected", "assertions", "pp_actor"):
            left.pop(name)
            right.pop(name)
        left["a"][0]["ability"] = right["a"][0]["ability"]
        assert left == right


@pytest.mark.parametrize("problem", [None, "no-hit", "callback", "cleanup", "other-outcome", "no-state", "no-pp"])
def test_only_a_clean_qualified_no_proc_window_is_inconclusive(problem):
    import live_dex_ability_probes as probes

    status = {"type": "status", "side": "B", "value": "par"}
    trigger = probes.Trigger("Static", "False Swipe", "outcomes", "A", probabilistic=True, assertions=(status,))
    states = observations()
    states[-1]["battle"]["sides"]["A"]["active"][0]["hp"] = 90
    result = {"status": "needs_diagnosis", "snapshots": states,
              "error": "Declared outcome not observed: " + json.dumps(status, sort_keys=True)}
    if problem == "no-hit":
        states[-1]["battle"]["sides"]["A"]["active"][0]["hp"] = 100
    elif problem == "callback":
        result["server_errors"] = [{"error": "Real callback failed"}]
    elif problem == "cleanup":
        result["cleanup_error"] = "Required staff fallback"
    elif problem == "other-outcome":
        result["error"] += "; Declared outcome not observed: missing damage"
    elif problem == "no-state":
        result["snapshots"] = []
    elif problem == "no-pp":
        result["error"] = "The tested move did not spend PP"
    assert probes.probability_window_unobserved(trigger, result) is (problem is None)


def test_status_cure_cannot_be_proven_by_switching_to_a_healthy_reserve():
    states = observations()
    states[0]["battle"]["sides"]["A"]["active"][0].update(id="owned:original", status="psn")
    part = states[-1]["battle"]["sides"]["A"]
    original = copy.deepcopy(part["active"][0]) | {"id": "owned:original", "status": "psn"}
    reserve = copy.deepcopy(part["active"][0]) | {"id": "owned:reserve", "status": ""}
    part.update(active=[reserve], pokemon=[original, reserve])
    case = probe(assertions=({"type": "not_status", "side": "A", "value": "psn", "original": True},))
    with pytest.raises(AssertionError, match="outcome not observed"):
        runner.evaluate(case, states, ["The healthy reserve entered."])
    original["status"] = ""
    assert runner.evaluate(case, states, ["The original Pokemon recovered on switching."])["status"] == "outcome_verified"


def test_item_transfer_requires_an_observed_item_change():
    states = observations()
    case = probe(assertions=({"type": "item", "side": "A", "value": "Lagging Tail"},))
    with pytest.raises(AssertionError, match="outcome not observed"):
        runner.evaluate(case, states, ["The item was stolen!"])
    states[-1]["battle"]["sides"]["A"]["active"][0]["item"] = "Laggingtail"
    assert runner.evaluate(case, states, ["The held item changed."])["status"] == "outcome_verified"
