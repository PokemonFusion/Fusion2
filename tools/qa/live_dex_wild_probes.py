"""Exercise wild-only escape and trapping rules using an ordinary QA login."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.qa import live_battle_pilot as pilot
from tools.qa.live_battle_pilot_cases import Mon
from tools.qa.live_dex_runner import DexRunner, now, verify


@dataclass(frozen=True)
class WildProbe:
    """One explicit escape precondition and its expected normal-command result."""

    key: str
    species: str
    ability: str
    foe_species: str
    foe_ability: str
    escapes: bool
    reason: str
    level: int = 100
    foe_level: int = 5


PROBES = (
    WildProbe("runaway-trap", "Eevee", "Run Away", "Trapinch", "Arena Trap", True, "runaway", 5, 100),
    WildProbe("arena-grounded", "Eevee", "No Ability", "Trapinch", "Arena Trap", False, "trapped"),
    WildProbe("arena-flying", "Pidgeot", "No Ability", "Trapinch", "Arena Trap", True, "faster"),
    WildProbe("arena-levitate", "Bronzong", "Levitate", "Trapinch", "Arena Trap", True, "faster"),
    WildProbe("arena-no-levitate", "Bronzong", "No Ability", "Trapinch", "Arena Trap", False, "trapped"),
    WildProbe("shadow-grounded", "Eevee", "No Ability", "Wobbuffet", "Shadow Tag", False, "trapped"),
    WildProbe("shadow-ghost", "Gastly", "No Ability", "Wobbuffet", "Shadow Tag", True, "faster"),
    WildProbe("shadow-mirror", "Wobbuffet", "Shadow Tag", "Wobbuffet", "Shadow Tag", True, "faster"),
    WildProbe("magnet-steel", "Magnezone", "No Ability", "Magnemite", "Magnet Pull", False, "trapped"),
    WildProbe("magnet-nonsteel", "Eevee", "No Ability", "Magnemite", "Magnet Pull", True, "faster"),
    WildProbe("magnet-ghost", "Aegislash", "No Ability", "Magnemite", "Magnet Pull", True, "faster"),
)


def evaluate(record):
    """Require actual flee state, ordinary permissions and complete cleanup."""
    probe = record["probe"]
    before, after = record["before"], record["after"]
    initial = before["battle"]
    assert initial and "WILD" in initial["type"].upper(), "A real wild battle did not start."
    assert initial["sides"]["A"]["active"][0]["species"] == probe["species"]
    assert initial["sides"]["B"]["active"][0]["ability"] == probe["foe_ability"]
    for state in (before, after):
        assert all(player["ordinary"] for player in state["players"].values()), "Battler has staff rights."
        frame = state.get("battle") or state.get("ended_battle") or {}
        assert not frame.get("callback_failures"), "Battle callback failed."
    frame = after.get("battle") or after.get("ended_battle") or {}
    flee = frame.get("flee_result", {})
    assert flee.get("success") is probe["escapes"], "Unexpected flee success: " + repr(flee)
    assert flee.get("reason") == probe["reason"], "Unexpected flee reason: " + repr(flee)
    assert bool(after["battle"]) is not probe["escapes"], "Escape did not produce the expected session state."
    cleanup = record["cleanup"]
    assert not cleanup["staff_cleanup_required"], "Cleanup required staff fallback."
    assert not cleanup["battle"] and not cleanup["room_battles"], "Wild battle remains active."
    assert all(not player["battle_lock"] and not player["battle_id"] for player in cleanup["players"].values())
    assert record["encounter_deleted"], "New temporary encounter was not deleted by normal cleanup."


def write_report(output, rows):
    """Keep wild proof separate from PvP entry and ability smoke coverage."""
    lines = ["# Ordinary-player wild encounter probes", "",
             f"{len(rows)}/{len(PROBES)} attempted. {dict(Counter(row['status'] for row in rows))}.", "",
             "Staff prepares a new temporary wild foe in the existing private QA room. The ordinary account uses +flee; "
             "remaining battles end with ordinary concession. Foes use Splash. Generated foe stats are observed, not matched "
             "between cases; escape assertions use trapping/guaranteed ability rules or an observed faster level-100 player against a level-5 foe. "
             "This does not test capture, rewards or every wild interaction.", "",
             "| Case | Result | Diagnosis |", "| --- | --- | --- |"]
    lines.extend(f"| {row['key']} | {row['status']} | {row.get('error', '')} |" for row in rows)
    (output / "wild-probes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(output):
    """Run fresh independent wild fixtures under the shared exclusive QA lock."""
    rows = []
    runner = DexRunner(output / "manifest.json")
    with pilot.run_lock(output):
        try:
            for label in ("staff", "a", "b"):
                runner.clients[label].open()
            runner.api = pilot.StaffAPI(runner.clients["staff"], runner.manifest, pilot.REPO / "tools/qa/live_dex_wild_server.py")
            runner.clean()
            for probe in PROBES:
                record = {"key": "wild-" + probe.key, "probe": asdict(probe), "status": "blocked", "started_utc": now()}
                reference = None
                try:
                    runner.api.call("setup", {"a": [asdict(Mon(probe.species, ("Splash",), probe.ability, level=probe.level))],
                                              "b": [asdict(Mon("Magikarp", ("Splash",), "No Ability"))]})
                    record["before"] = runner.api.call("start_wild", {"species": probe.foe_species, "level": probe.foe_level,
                                                                     "ability": probe.foe_ability, "seed": 104729})
                    reference = record["before"]["new_encounter_ref"]
                    record["output"] = runner.clients["a"].send("+flee")
                    record["after"] = runner.api.call("snapshot")
                except Exception as error:
                    record["error"] = str(error)
                finally:
                    try:
                        record["cleanup"] = runner.clean()
                        record["encounter_deleted"] = reference is not None and not runner.api.call("encounter_exists", {"ref": reference})["exists"]
                        if "after" in record:
                            try:
                                evaluate(record)
                                record["status"] = "outcome_verified"
                            except AssertionError as error:
                                record.update(status="needs_diagnosis", error=str(error))
                    except Exception as error:
                        record.update(status="blocked", cleanup_error=str(error))
                record["completed_utc"] = now()
                folder = output / "evidence"
                folder.mkdir(exist_ok=True)
                target = folder / (record["key"] + ".json.gz")
                if target.exists():
                    attempts = output / "attempts"
                    attempts.mkdir(exist_ok=True)
                    target.replace(attempts / (record["key"] + "-" + str(time.time_ns()) + ".json.gz"))
                with gzip.open(target, "wt", encoding="utf-8") as stream:
                    json.dump(record, stream, default=str)
                row = {name: record[name] for name in ("key", "status", "completed_utc", "error", "cleanup_error") if name in record}
                row["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
                rows.append(row)
                pilot.save(output / "wild-probes.json", rows)
                write_report(output, rows)
                print(json.dumps(row), flush=True)
                safety = verify(output, audit=False, quiet=True)
                assert safety["protected_rows_unchanged"] and safety["user_wip_unchanged"], "Protected baseline changed."
                if record.get("cleanup_error") or record.get("cleanup", {}).get("staff_cleanup_required"):
                    break
        finally:
            for client in runner.clients.values():
                client.close()
    return rows


def audit(output):
    """Re-evaluate exact saved observations and their checksum bindings."""
    rows = json.loads((output / "wild-probes.json").read_text(encoding="utf-8"))
    errors, count = [], 0
    for row in rows:
        if row["status"] != "outcome_verified":
            continue
        try:
            path = output / "evidence" / (row["key"] + ".json.gz")
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                evaluate(json.load(stream))
            count += 1
        except Exception as error:
            errors.append({"key": row["key"], "error": str(error)})
    result = {"audited": count, "errors": errors}
    pilot.save(output / "wild-probes-audit.json", result)
    return result


def main():
    """Execute or audit wild probes inside an already prepared local QA run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "audit"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(pilot.ARTIFACTS) or output == pilot.ARTIFACTS:
        parser.error("Output must be an existing run inside .codex-artifacts.")
    if args.action == "run":
        run(output)
    else:
        result = audit(output)
        print(json.dumps(result))
        if result["errors"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
