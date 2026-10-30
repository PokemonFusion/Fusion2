"""Map every original smoke entry to retained, independently audited effect proof."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.qa.live_dex_cases import key
from tools.qa.live_dex_runner import now
from tools.qa import live_battle_pilot as pilot


class EffectCoverage:
    """Keep historical raw smoke labels separate from newer qualified evidence."""

    def __init__(self, original, output):
        self.original, self.output = original, output

    def read(self, name, default=None):
        """Read a current phase index without inventing missing evidence."""
        path = self.output / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

    def reference(self, filename, row):
        """Retain the exact row and all existing command/state content hashes."""
        return {"index": filename, "row": row}

    def build(self, require_complete=False):
        """Map exactly the 108 move and 266 ability raw smoke entries."""
        original_rows = json.loads((self.original / "results.json").read_text(encoding="utf-8"))
        targets = [row for row in original_rows if row["status"] == "smoke_completed"]
        assert Counter(row["kind"] for row in targets) == {"move": 108, "ability": 266}
        ability_proof = {}
        for filename in ("ability-probes.json", "extra-ability-probes.json", "gap-probes.json"):
            for row in self.read(filename, []):
                positive = row.get("positive_trigger", row.get("trigger", {}).get("direction") != "equal")
                if row["status"] == "outcome_verified" and positive:
                    ability_proof.setdefault(key(row["ability"]), []).append(self.reference(filename, row))
        for row in self.read("post-battle-probes.json", []):
            if row["status"] == "outcome_verified" and row["variant"] and row["observed_item"]:
                ability_proof.setdefault(key(row["ability"]), []).append(self.reference("post-battle-probes.json", row))
        wild = {row["key"]: row for row in self.read("wild-probes.json", [])}
        for name, case in (("Run Away", "wild-runaway-trap"), ("Arena Trap", "wild-arena-grounded"),
                           ("Shadow Tag", "wild-shadow-grounded"), ("Magnet Pull", "wild-magnet-steel")):
            if wild.get(case, {}).get("status") == "outcome_verified":
                ability_proof.setdefault(key(name), []).append(self.reference("wild-probes.json", wild[case]))
        tera = {row["key"]: row for row in self.read("tera-results.json", [])}
        native = "01-clear-both-damaged-native"
        if tera.get(native, {}).get("status") == "passed":
            proof = self.reference("tera-results.json", tera[native])
            proof["sha256"] = hashlib.sha256((self.output / "tera-evidence" / (native + ".json.gz")).read_bytes()).hexdigest()
            ability_proof.setdefault("teraformzero", []).append(proof)
        moves = {row["subject"]: row for row in self.read("move-effect-results.json", [])}
        null = self.read("null-ability-results.json", [])
        entries = []
        for target in targets:
            original_file = self.original / "evidence" / (target["key"] + ".json.gz")
            row = {"key": target["key"], "subject": target["subject"], "kind": target["kind"],
                   "original_status": "smoke_completed", "original_sha256": hashlib.sha256(original_file.read_bytes()).hexdigest(),
                   "status": "unverified", "evidence": []}
            if target["kind"] == "ability":
                row["evidence"] = ability_proof.get(key(target["subject"]), [])
                if row["evidence"]:
                    row["status"] = "effect_verified"
                if key(target["subject"]) == "noability" and null and null[0]["status"] == "outcome_verified":
                    row.update(status="expected_no_effect_verified", evidence=[self.reference("null-ability-results.json", null[0])])
            else:
                qualified = moves.get(target["subject"])
                if qualified:
                    row["status"] = "effect_verified" if qualified["status"] == "outcome_verified" else qualified["status"]
                    row["evidence"] = [self.reference("move-effect-results.json", qualified)]
            entries.append(row)
        counts = dict(Counter(row["status"] for row in entries))
        pending = [row["key"] for row in entries if row["status"] not in {"effect_verified", "expected_no_effect_verified"}]
        report = {"generated_utc": now(), "target_entries": len(targets), "counts": counts, "pending": pending,
                  "original_run": str(self.original), "qualified_run": str(self.output), "entries": entries,
                  "scope": "Declared actual effect per original subject; not every interaction, generation variant, or natural progression path."}
        pilot.save(self.output / "smoke-effect-coverage.json", report)
        if require_complete:
            assert not pending, pending
            assert counts == {"effect_verified": 373, "expected_no_effect_verified": 1}, counts
            for filename in ("ability-probes-audit.json", "extra-ability-audit.json", "wild-probes-audit.json", "move-effect-audit.json"):
                audit = self.read(filename)
                assert audit is not None and not audit["errors"], filename
        return {name: report[name] for name in ("generated_utc", "target_entries", "counts", "pending", "scope")}


def main():
    """Build the explicit 374-entry mapping only inside ignored local QA roots."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    original, output = args.original.resolve(), args.output.resolve()
    assert all(path.is_relative_to(pilot.ARTIFACTS) and path != pilot.ARTIFACTS for path in (original, output))
    print(json.dumps(EffectCoverage(original, output).build(args.require_complete)))


if __name__ == "__main__":
    main()
