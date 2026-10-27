"""Prevent completion messages, PP use, or expected misses becoming effect proof."""

import copy
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from live_dex_runner import evaluate, has_server_error
from live_smoke_effects import EffectEvaluator
from live_smoke_effects_cases import EffectProbe, actor, check, probes, scenario


def retained(case, damage=0):
    """Build independent complete observations with real owned PP fields."""
    move = case.a[0].moves[0]
    pokemon = {"species": "Mew", "hp": 100, "max_hp": 100, "types": ["Psychic"],
               "ability": "No Ability", "boosts": {}, "status": "", "ability_state": {},
               "moves": [{"move__name": move, "current_pp": 10}]}
    state = {"players": {label: {"ordinary": True, "pokemon": [copy.deepcopy(pokemon) | {"id": label}]} for label in ("a", "b")},
             "battle": {"turn": 1, "field": {}, "sides": {side: {"active": [copy.deepcopy(pokemon)]} for side in ("A", "B")}}}
    end = copy.deepcopy(state)
    end["battle"]["turn"] = 2
    end["battle"]["sides"]["B"]["active"][0]["hp"] -= damage
    end["players"]["a"]["pokemon"][0]["moves"][0]["current_pp"] -= 1
    return {"snapshots": [state, end], "outputs": [], "cleanup": {"room_clear": True, "locks_clear": True, "staff_cleanup_required": False}}


def test_normal_critical_capture_text_is_not_an_exception():
    assert not has_server_error("2026-10-19 00:51:24,576 A critical capture!")
    for text in ("Traceback (most recent call last):", "[EE] handler failed", "callback failure", "Unhandled exception", "2026-10-19 CRITICAL failure"):
        assert has_server_error(text)


def test_expected_accuracy_miss_cannot_supply_a_missing_effect():
    case = replace(scenario("Assist", assertions=(check("damage", "B"),)), raw={"accuracy": 80})
    record = retained(case)
    record["outputs"] = ["Assist missed!"]
    record["status"] = evaluate(case, record["snapshots"], record["outputs"])["status"]
    assert record["status"] == "expected_failure"
    with pytest.raises(AssertionError, match="Declared outcome not observed"):
        EffectEvaluator().assess(EffectProbe("Assist", (case,)), [record])


def test_pp_and_completed_turn_are_insufficient_without_an_effect_contract():
    case = scenario("Assist")
    record = retained(case)
    record["status"] = "smoke_completed"
    with pytest.raises(AssertionError, match="No actual effect"):
        EffectEvaluator().assess(EffectProbe("Assist", (case,)), [record])


@pytest.mark.parametrize("damage,accepted", [(20, False), (10, False), (35, True)])
def test_directional_effect_requires_observed_change(damage, accepted):
    case = scenario("Electro Ball")
    left, right = retained(case, 20), retained(case, damage)
    probe = EffectProbe("Electro Ball", (case, case))
    if accepted:
        fact = EffectEvaluator().rule(probe, [left, right], {"type": "damage_relation", "relation": "greater"})
        assert fact["variant_damage"] == 35
    else:
        with pytest.raises(AssertionError):
            EffectEvaluator().rule(probe, [left, right], {"type": "damage_relation", "relation": "greater"})


def test_unequal_attack_and_defense_must_actually_swap():
    case = scenario("Power Shift", a=(actor(("Power Shift",), "Shuckle"),))
    record = retained(case)
    start, end = record["snapshots"]
    start["battle"]["sides"]["A"]["active"][0]["stats"] = {"atk": 20, "def": 235}
    current = end["battle"]["sides"]["A"]["active"][0]
    current["stats"] = {"atk": 20, "def": 235}
    probe = EffectProbe("Power Shift", (case,))
    with pytest.raises(AssertionError):
        EffectEvaluator().rule(probe, [record], {"type": "attack_defense_swap"})
    current["stats"] = {"atk": 235, "def": 20}
    EffectEvaluator().rule(probe, [record], {"type": "attack_defense_swap"})


def test_all_former_smoke_moves_have_unique_legal_sized_prepared_cases():
    expected = set("Acupressure|After You|Aromatherapy|Assist|Attract|Baneful Bunker|Beat Up|Belly Drum|Bestow|Block|Burning Bulwark|Confuse Ray|Copycat|Corrosive Gas|Crush Grip|Curse|Defog|Destiny Bond|Detect|Disable|Doodle|Dragon Cheer|Electrify|Electro Ball|Embargo|Encore|Endure|Entrainment|Fissure|Flail|Focus Energy|Follow Me|Foresight|Frustration|Gastro Acid|Grass Knot|Grudge|Guillotine|Gyro Ball|Hard Press|Heal Bell|Heal Block|Heat Crash|Heavy Slam|Helping Hand|Horn Drill|Imprison|Instruct|King's Shield|Laser Focus|Leech Seed|Lock-On|Low Kick|Magnet Rise|Magnitude|Max Guard|Mean Look|Metronome|Mind Reader|Miracle Eye|Natural Gift|Nature Power|Nightmare|Obstruct|Octolock|Odor Sleuth|Pain Split|Parting Shot|Pika Papow|Powder|Power Shift|Power Trick|Protect|Punishment|Purify|Quash|Rage Powder|Recycle|Refresh|Return|Reversal|Role Play|Shed Tail|Silk Trap|Simple Beam|Skill Swap|Spider Web|Spiky Shield|Spit Up|Spotlight|Stockpile|Strength Sap|Supersonic|Swallow|Sweet Kiss|Switcheroo|Take Heart|Taunt|Teeter Dance|Telekinesis|Tidy Up|Torment|Trick|Trump Card|Veevee Volley|Venom Drench|Worry Seed|Wring Out".split("|"))
    plan = probes()
    assert {probe.subject for probe in plan} == expected
    keys = [case.key for probe in plan for case in probe.cases]
    assert len(set(keys)) == len(keys)
    for probe in plan:
        assert probe.rules or all(case.assertions for case in probe.cases)
        for case in probe.cases:
            assert all(1 <= len(mon.moves) <= 4 and len(set(mon.moves)) == len(mon.moves) for mon in case.a + case.b)
