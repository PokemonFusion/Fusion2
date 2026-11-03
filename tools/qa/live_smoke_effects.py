"""Run and audit actual move effects through disposable localhost player logins."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.qa import live_battle_pilot as pilot
from tools.qa.live_dex_cases import from_dict, key
from tools.qa.live_dex_runner import DexRunner, evaluate, mon, now, original_mon, side_pp, verify
from tools.qa.live_smoke_effects_cases import EffectProbe, no_ability_probe, probes


class ChanceNotObserved(AssertionError):
    """A qualifying natural opportunity occurred without its requested branch."""


def frame(record, index=-1):
    """Read an observed frame, including normally completed battles."""
    state = record["snapshots"][index]
    return state.get("battle") or state.get("ended_battle") or {}


def pokemon(record, index=-1, side="A", slot=0):
    """Follow original owned identities across switching, fainting and cleanup."""
    states = record["snapshots"]
    return original_mon(states[index], states[0], side, slot)


def loss(record, side="B", slot=0, start=-2, end=-1):
    """Measure damage in the final attack window, excluding setup turns."""
    return pokemon(record, start, side, slot)["hp"] - pokemon(record, end, side, slot)["hp"]


class EffectEvaluator:
    """Require independent observable outcomes instead of trusting success text."""

    def assess(self, probe, records):
        """Check baseline execution integrity and every declared effect rule."""
        assert len(records) == len(probe.cases)
        for case, record in zip(probe.cases, records):
            assert record["status"] in {"outcome_verified", "smoke_completed", "expected_failure"}, record.get("error", record["status"])
            assert len(record["snapshots"]) >= 2
            assert not record.get("server_errors") and not record.get("cleanup_error")
            cleanup = record["cleanup"]
            assert cleanup["room_clear"] and cleanup["locks_clear"] and not cleanup["staff_cleanup_required"]
            checked = evaluate(case, record["snapshots"], record["outputs"])
            assert checked["status"] == record["status"]
            # Failure text can explain a missing outcome in the broad runner.
            # It must never excuse an actual-effect assertion in this runner.
            independent = evaluate(case, record["snapshots"], [])
            assert independent["status"] in {"outcome_verified", "smoke_completed"}
            for state in record["snapshots"]:
                assert all(player["ordinary"] for player in state["players"].values())
                current = state.get("battle") or state.get("ended_battle") or {}
                assert not current.get("callback_failures")
        assert probe.rules or all(case.assertions for case in probe.cases), "No actual effect is declared."
        facts = []
        for rule in probe.rules:
            facts.append(self.rule(probe, records, rule))
        return facts

    def rule(self, probe, records, rule):
        """Interpret a small explicit effect vocabulary against retained state."""
        record = records[-1]
        before, after = pokemon(record, 0), pokemon(record)
        kind = rule["type"]
        fact = {"type": kind}
        if kind == "damage_relation":
            left, right = (loss(item) for item in records)
            if rule.get("critical_control"):
                # These fixtures use an unboosted, non-STAB physical Slash
                # against the same itemless/abilityless target. A naturally
                # critical control cannot demonstrate additional critical gain.
                slot = 1 if probe.cases[0].mode == "double" else 0
                user, target = pokemon(records[0], 0, slot=slot), pokemon(records[0], 0, "B")
                assert "Normal" not in user["types"]
                level = probe.cases[0].a[slot].level
                maximum_normal = ((2 * level // 5 + 2) * 70 * user["stats"]["atk"] // target["stats"]["def"]) // 50 + 2
                if left > maximum_normal:
                    raise ChanceNotObserved("The unassisted Slash control was already critical; use a bounded fresh control window.")
            assert min(left, right) > 0, (left, right)
            assert (right > left) if rule["relation"] == "greater" else (right < left), (left, right, rule)
            if rule["relation"] == "greater" and "minimum_ratio" in rule:
                assert right / left >= rule["minimum_ratio"], (left, right, rule)
            if rule["relation"] == "less" and "maximum_ratio" in rule:
                assert right / left <= rule["maximum_ratio"], (left, right, rule)
            fact.update(control_damage=left, variant_damage=right)
        elif kind == "no_ability":
            assert key(before["ability"]) == key(after["ability"]) == "noability"
            assert loss(records[0]) == loss(records[1]) > 0
            assert not after["status"] and all(not value for value in after["boosts"].values())
            fact["matched_damage"] = loss(record)
        elif kind == "one_random_boost":
            changed = {name: value for name, value in after["boosts"].items() if value != before["boosts"].get(name, 0)}
            assert len(changed) == 1 and list(changed.values()) == [rule["amount"]], changed
            fact["changed"] = changed
        elif kind == "party_cure":
            states = record["snapshots"]
            assert all(item["status"] for item in states[0]["players"]["a"]["pokemon"])
            assert all(not item["status"] for item in states[-1]["players"]["a"]["pokemon"])
        elif kind in {"hp_cost", "heal_fraction"}:
            amount = before["max_hp"] * rule["numerator"] // rule["denominator"]
            expected = before["hp"] - amount if kind == "hp_cost" else min(before["max_hp"], before["hp"] + amount)
            assert after["hp"] == expected, (before["hp"], after["hp"], expected)
            fact.update(before_hp=before["hp"], after_hp=after["hp"], expected=expected)
        elif kind == "exact_hp":
            assert after["hp"] == rule["value"]
        elif kind == "pain_split":
            expected = (before["hp"] + pokemon(record, 0, "B")["hp"]) // 2
            for side in ("A", "B"):
                current = pokemon(record, -1, side)
                assert current["hp"] == min(current["max_hp"], expected), (side, current, expected)
        elif kind == "strength_sap":
            attack = pokemon(record, 0, "B")["stats"]["atk"]
            assert after["hp"] == min(before["max_hp"], before["hp"] + attack)
        elif kind in {"leech_seed", "target_loss_fraction"}:
            numerator, denominator = (1, 8) if kind == "leech_seed" else (rule["numerator"], rule["denominator"])
            amount = pokemon(record, 0, "B")["max_hp"] * numerator // denominator
            for index in range(1, len(record["snapshots"])):
                assert loss(record, start=index - 1, end=index) == amount
                if kind == "leech_seed":
                    old, new = pokemon(record, index - 1), pokemon(record, index)
                    assert new["hp"] == min(old["max_hp"], old["hp"] + amount)
        elif kind in {"stored_items", "checkpoint_items"}:
            if kind == "stored_items":
                final = record["snapshots"][-1]["players"]
                assert key(final["a"]["pokemon"][0]["item"]) == key(rule["a"])
                assert key(final["b"]["pokemon"][0]["item"]) == key(rule["b"])
            else:
                for index in (1, 2):
                    assert key(pokemon(record, index)["item"]) == key(rule["a"])
                    assert key(pokemon(record, index, "B")["item"]) == key(rule["b"])
        elif kind == "executed_type":
            assert after["executed_move"]["type"] == rule["value"]
        elif kind == "recycle":
            assert not before["item"] and key(after["item"]) == "oranberry"
        elif kind == "gastro_acid":
            assert "gastroacid" in pokemon(record, 1, "B")["volatiles"]
            assert loss(record) > 0
        elif kind == "stockpile":
            assert pokemon(record, 2)["effect_state"]["stockpile_layers"] == 2
            assert after["effect_state"]["stockpile_layers"] == (0 if rule["consumed"] else 3)
            if probe.subject == "Swallow":
                initial = pokemon(record, 2)
                assert after["hp"] == min(after["max_hp"], initial["hp"] + after["max_hp"] // 2)
        elif kind == "attack_defense_swap":
            assert after["stats"]["atk"] == before["stats"]["def"]
            assert after["stats"]["def"] == before["stats"]["atk"]
        elif kind == "blocked_switch":
            old, new = pokemon(record, 0, "B"), mon(record["snapshots"][-1], "B")
            assert old["id"] == new["id"]
            text = "\n".join(record["outputs"]).lower()
            assert "trap" in text or "cannot switch" in text or "can't switch" in text
        elif kind == "restricted_command":
            name = rule["effect"]
            target = pokemon(record, -1, "B")
            applied = 2 if name in {"disable", "encore", "torment"} else 1
            initial = record["snapshots"][applied]
            final = record["snapshots"][-1]
            holder = pokemon(record, applied, "A" if name == "imprison" else "B")
            assert name in holder["volatiles"], (name, holder["volatiles"])
            if name == "embargo":
                assert key(target["item"]) == "leftovers"
                assert target["hp"] == pokemon(record, 0, "B")["hp"], "Embargo failed to suppress Leftovers healing."
            elif name == "encore":
                assert side_pp(initial, "B", "Water Gun") == side_pp(final, "B", "Water Gun")
                assert 1 <= side_pp(initial, "B", "Tackle") - side_pp(final, "B", "Tackle") <= 2
            else:
                assert side_pp(initial, "B", rule["move"]) == side_pp(final, "B", rule["move"]), "Restricted move spent PP."
                assert 1 <= side_pp(initial, "B", "Water Gun") - side_pp(final, "B", "Water Gun") <= 2
        elif kind == "destiny_bond":
            assert pokemon(record, -1, "B")["hp"] == 0
        elif kind == "grudge":
            assert side_pp(record["snapshots"][-1], "B", "Water Gun") == 0
        elif kind in {"called_move", "called_effect"}:
            called = [name for index in range(1, len(record["snapshots"])) for name in frame(record, index).get("called_moves", [])]
            assert called, "No called move was retained."
            if kind == "called_move":
                assert key(rule["value"]) in {key(name) for name in called}, called
            else:
                if not any(pokemon(record, index, "B")["hp"] < pokemon(record, 0, "B")["hp"] for index in range(1, len(record["snapshots"]))):
                    raise ChanceNotObserved("Called moves executed, but no damaging positive branch occurred in the bounded window.")
            fact["called_moves"] = called
        elif kind == "instruct":
            values = [side_pp(state, "B", "Tackle") for state in record["snapshots"]]
            assert values == [35, 34, 32], values
            assert loss(record, "A") > 0
            assert "Instruct and called Tackle" in "\n".join(record["outputs"])
            fact["target_pp"] = values
        elif kind in {"confusion", "infatuation"}:
            volatile = "attract" if kind == "infatuation" else "confusion"
            assert any(volatile in pokemon(record, index, "B")["volatiles"] for index in range(1, len(record["snapshots"]))), "The primary volatile never applied."
            if kind == "confusion":
                if pokemon(record, -1, "B")["hp"] >= pokemon(record, 0, "B")["hp"]:
                    raise ChanceNotObserved("Confusion applied, but no self-hit occurred in its bounded duration.")
            else:
                used = side_pp(record["snapshots"][0], "B", "Tackle") - side_pp(record["snapshots"][-1], "B", "Tackle")
                if used == len(record["snapshots"]) - 1:
                    raise ChanceNotObserved("Attract applied, but no immobilization occurred in the bounded window.")
                fact["tackle_pp_spent"] = used
        elif kind == "magnitude":
            values = [[pokemon(record, index)["executed_move"].get("magnitude"), pokemon(record, index)["executed_move"].get("power")] for index in range(1, len(record["snapshots"]))]
            expected = {4: 10, 5: 30, 6: 50, 7: 70, 8: 90, 9: 110, 10: 150}
            assert all(expected.get(level) == power for level, power in values), values
            if len({power for _, power in values}) < 2:
                raise ChanceNotObserved("Magnitude executed, but only one natural power occurred in the bounded window.")
            fact["selected_levels_and_power"] = values
        elif kind == "accuracy_control":
            control, actual = (loss(item) for item in records)
            if control > 0:
                raise ChanceNotObserved("The unassisted accuracy control hit; this pair cannot demonstrate the lock-on benefit.")
            assert actual > 0
            fact.update(control_damage=control, locked_damage=actual)
        elif kind == "parting_shot":
            assert all(pilot.stage(pokemon(record, -1, "B"), stat) == -1 for stat in ("atk", "spa"))
        elif kind == "shed_tail":
            assert before["hp"] - after["hp"] == (before["max_hp"] + 1) // 2
            replacement = mon(record["snapshots"][-1])
            substitute = replacement["volatile_state"].get("substitute")
            assert isinstance(substitute, dict) and substitute["hp"] == max(1, (before["max_hp"] + 3) // 4)
        elif kind == "field_cleanup":
            initial = frame(record, 1)
            assert all("spikes" in initial["sides"][side]["conditions"] for side in ("A", "B")), "Hazard setup did not qualify."
            final = frame(record)
            assert all("spikes" not in final["sides"][side]["conditions"] for side in ("A", "B"))
            if rule["move"] == "defog":
                assert "reflect" in final["sides"]["A"]["conditions"]
                assert "reflect" not in final["sides"]["B"]["conditions"]
                assert final["field"]["terrain"] in {"", "None", None}
            else:
                assert all("substitute" not in pokemon(record, -1, side)["volatiles"] for side in ("A", "B"))
                assert pilot.stage(after, "atk") == pilot.stage(after, "spe") == 1
        elif kind == "electrify":
            assert loss(record, "A", start=0, end=1) == 0
            assert pokemon(record, 1, "B")["executed_move"]["type"] == "Electric"
            assert pokemon(record, 2, "B")["executed_move"]["type"] == "Normal"
            assert loss(record, "A") > 0
        elif kind == "powder":
            assert loss(record, "A") == 0
            assert loss(record) == pokemon(record, 0, "B")["max_hp"] // 4
        elif kind == "queue_order":
            control, actual = records
            assert loss(control, "A", 1) > 0 and loss(actual, "A", 1) == 0
            assert pokemon(actual, -1, "B")["hp"] == 0
            assert side_pp(actual["snapshots"][0], "B", "Water Gun") == side_pp(actual["snapshots"][-1], "B", "Water Gun")
        elif kind == "redirection":
            control, actual = records
            recipient = rule["recipient"]
            assert loss(control, "A", 1 - recipient) > 0
            assert loss(actual, "A", recipient) > 0 and loss(actual, "A", 1 - recipient) == 0
        else:
            raise AssertionError("Unknown effect rule: " + kind)
        return fact


class EffectStaffAPI(pilot.StaffAPI):
    """Attach canonical fixture data only to the guarded pre-battle setup call."""

    fixture = None

    def call(self, action, payload=None):
        """No live battle state, hooks or RNG outcomes are replaced."""
        if action == "setup" and self.fixture:
            payload = dict(payload or {}, effect_fixture=self.fixture)
        return super().call(action, payload)


class MoveEffectRunner:
    """Retain every attempt, diagnose flags, and audit original smoke mappings."""

    def __init__(self, output):
        self.output = output
        self.evaluator = EffectEvaluator()

    def run(self, selected=None, seed_offset=0, plan=None, index_name="move-effect-results.json"):
        """Execute all exact cases exclusively and preserve failed attempts."""
        while (self.output / "automated-gate-active").exists():
            time.sleep(10)
        runner = DexRunner(self.output / "manifest.json")
        path = self.output / index_name
        rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        previous = {row["subject"]: row for row in rows}
        plan = probes() if plan is None else plan
        pilot.save(self.output / index_name.replace("results.json", "plan.json"), [asdict(probe) for probe in plan])
        sources = {name: (pilot.REPO / "tools" / "qa" / name).read_bytes() for name in
                   ("live_smoke_effects.py", "live_smoke_effects_cases.py", "live_smoke_effects_server.py")}
        source_hashes = {name: hashlib.sha256(content).hexdigest() for name, content in sources.items()}
        source_group = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
        folder = self.output / "qa-source" / source_group
        folder.mkdir(parents=True, exist_ok=True)
        for name, content in sources.items():
            destination = folder / name
            if destination.exists():
                assert destination.read_bytes() == content
            else:
                destination.write_bytes(content)
        pilot.save(folder / "sha256.json", source_hashes)
        with pilot.run_lock(self.output):
            try:
                for client in runner.clients.values():
                    client.open()
                runner.api = EffectStaffAPI(runner.clients["staff"], runner.manifest, pilot.REPO / "tools/qa/live_smoke_effects_server.py")
                runner.clean()
                for probe in plan:
                    if selected and key(probe.subject) not in selected:
                        continue
                    if not selected and probe.subject in previous:
                        continue
                    row = {"subject": probe.subject, "original_key": ("ability-" if probe.subject == "No Ability" else "move-") + key(probe.subject),
                           "started_utc": now(), "status": "needs_diagnosis", "cases": [], "scope": probe.scope,
                           "rules": probe.rules, "fixture": probe.fixture}
                    row["probe"] = asdict(probe)
                    row["qa_source_group"] = source_group
                    records = []
                    for index, case in enumerate(probe.cases):
                        runner.api.fixture = probe.fixture[index] if probe.fixture else None
                        record = runner.run_case(case, seed_offset)
                        records.append(record)
                        digest = hashlib.sha256((self.output / "evidence" / (case.key + ".json.gz")).read_bytes()).hexdigest()
                        row["cases"].append({"key": case.key, "sha256": digest, "raw_status": record["status"]})
                        assert not record.get("cleanup_error") and not record["cleanup"]["staff_cleanup_required"]
                    try:
                        row["observed_effects"] = self.evaluator.assess(probe, records)
                        row["status"] = "outcome_verified"
                    except ChanceNotObserved as error:
                        assert probe.chance
                        row.update(status="chance_not_observed", error=str(error))
                    except AssertionError as error:
                        row["error"] = str(error)
                        import traceback
                        row["qualification_traceback"] = traceback.format_exc()
                    row["completed_utc"] = now()
                    if probe.subject in previous:
                        attempts = self.output / "effect-result-attempts"
                        attempts.mkdir(exist_ok=True)
                        pilot.save(attempts / (key(probe.subject) + "-" + str(__import__("time").time_ns()) + ".json"), previous[probe.subject])
                    previous[probe.subject] = row
                    pilot.save(path, list(previous.values()))
                    print(json.dumps(row, ensure_ascii=True), flush=True)
                    safety = verify(self.output, audit=False, quiet=True)
                    assert safety["protected_rows_unchanged"] and safety["user_wip_unchanged"]
            finally:
                for client in runner.clients.values():
                    client.close()
        return list(previous.values())

    def audit(self):
        """Re-evaluate exact retained stimuli and checksums without gameplay."""
        rows = json.loads((self.output / "move-effect-results.json").read_text(encoding="utf-8"))
        errors = []
        for row in rows:
            if row["status"] != "outcome_verified":
                continue
            try:
                records = []
                for entry in row["cases"]:
                    path = self.output / "evidence" / (entry["key"] + ".json.gz")
                    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
                    records.append(json.loads(gzip.decompress(path.read_bytes())))
                saved = dict(row["probe"])
                saved["cases"] = tuple(from_dict(case) for case in saved["cases"])
                saved["rules"] = tuple(saved["rules"])
                saved["fixture"] = tuple(saved["fixture"])
                assert self.evaluator.assess(EffectProbe(**saved), records) == row["observed_effects"]
            except Exception as error:
                errors.append({"subject": row["subject"], "error": str(error)})
        report = {"audited_outcomes": sum(row["status"] == "outcome_verified" for row in rows),
                  "counts": dict(Counter(row["status"] for row in rows)), "errors": errors, "verified_utc": now()}
        pilot.save(self.output / "move-effect-audit.json", report)
        assert not errors, errors
        return report


def main():
    """Run fresh ordinary-login effects or audit existing retained proof."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "audit", "null-ability"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--move", action="append", default=[])
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--rerun-all", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to(pilot.ARTIFACTS) and output != pilot.ARTIFACTS
    runner = MoveEffectRunner(output)
    if args.action == "null-ability":
        result = runner.run(selected={"noability"}, seed_offset=args.seed_offset,
                            plan=(no_ability_probe(),), index_name="null-ability-results.json")
    else:
        selected = {key(probe.subject) for probe in probes()} if args.rerun_all else {key(name) for name in args.move}
        result = runner.run(selected, args.seed_offset) if args.action == "run" else runner.audit()
    print(json.dumps(result if isinstance(result, dict) else {"counts": dict(Counter(row["status"] for row in result))}))


if __name__ == "__main__":
    main()
