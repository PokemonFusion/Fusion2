"""Index exact local live evidence without turning smoke into mechanic proof."""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.qa import live_battle_pilot as pilot
from tools.qa.live_dex_cases import key
from tools.qa.live_dex_runner import now


class CoverageIndex:
    """Join immutable case definitions, catalog results and matched experiments."""

    def __init__(self, output):
        self.output = output

    def read(self, name, default=None):
        """Read a UTF-8 index after the live worker has released its lock."""
        path = self.output / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

    def build(self):
        """Keep declared assertions, limitations and unresolved triggers explicit."""
        pinned = {case["key"]: case for case in self.read("catalog.json", [])}
        pairs = defaultdict(list)
        for row in self.read("ability-probes.json", []):
            pairs[key(row["ability"])].append(row)
        additional = self.read("extra-ability-probes.json", [])
        if additional:
            audit = self.read("extra-ability-audit.json", {})
            assert audit.get("attempted") == len(additional) and not audit.get("errors"), "Additional comparisons need their own completed audit."
            for row in additional:
                pairs[key(row["ability"])].append(row)
        entries = []
        for row in self.read("results.json", []):
            with gzip.open(self.output / "evidence" / (row["key"] + ".json.gz"), "rt", encoding="utf-8") as stream:
                evidence = json.load(stream)
            case = evidence.get("case", pinned.get(row["key"], {}))
            item = {"key": row["key"], "kind": row["kind"], "subject": row["subject"], "status": row["status"],
                    "assertions": case.get("assertions", []), "limitations": case.get("limitations", []),
                    "evidence": "evidence/" + row["key"] + ".json.gz",
                    "runtime_flags": evidence["snapshots"][0].get("runtime", {}) if evidence.get("snapshots") else {},
                    "loaded_code_versions": evidence["snapshots"][0].get("loaded_code_versions", {}) if evidence.get("snapshots") else {},
                    "complete_mechanics_verified": False}
            if row["kind"] == "ability":
                experiments = pairs[key(row["subject"])]
                item["matched_positive_triggers"] = [pair["key"] for pair in experiments
                                                     if pair["status"] == "outcome_verified" and pair.get("positive_trigger", pair["trigger"]["direction"] != "equal")]
                item["matched_negative_controls"] = [pair["key"] for pair in experiments
                                                     if pair["status"] == "outcome_verified" and not pair.get("positive_trigger", pair["trigger"]["direction"] != "equal")]
                item["unresolved_experiments"] = [pair["key"] for pair in experiments if pair["status"] != "outcome_verified"]
                raw = case.get("raw", {})
                item["declared_hooks"] = [name for name in raw if name.startswith("on")]
            entries.append(item)
        catalog = [row for row in entries if row["kind"] != "regression"]
        abilities = [row for row in catalog if row["kind"] == "ability"]
        pending = [row for row in abilities if not row["matched_positive_triggers"]]
        summary = {"generated_utc": now(), "catalog_entries_attempted": len(catalog),
                   "catalog_statuses": dict(Counter(row["status"] for row in catalog)),
                   "abilities_with_a_matched_positive_trigger": sum(bool(row["matched_positive_triggers"]) for row in abilities),
                   "abilities_without_a_matched_positive_trigger": len(pending),
                   "complete_mechanics_verified": False,
                   "scope": "Catalog execution plus declared assertions and matched triggers only; no all-interactions or production-readiness claim."}
        pilot.save(self.output / "coverage-index.json", {"summary": summary, "entries": entries})
        pilot.save(self.output / "ability-trigger-gaps.json", pending)
        lines = ["# Live coverage scope", "", f"Generated {summary['generated_utc']}.", "",
                 f"{len(catalog)} catalog entries have retained real-login attempts. "
                 f"{summary['abilities_with_a_matched_positive_trigger']}/{len(abilities)} abilities have at least one verified matched positive trigger; "
                 f"{len(pending)} still need a matched positive trigger. These counts do not establish complete mechanics.", "",
                 "Species probes cover prepared entry identity/types and a normal action. Move outcomes cover only saved assertions; "
                 "secondary probabilities, alternative targets and custom branches may remain untested. A successful negative control "
                 "does not supply a missing positive trigger.", "",
                 "`coverage-index.json` records every exact assertion, limitation, evidence path and observed runtime version flags. "
                 "`ability-trigger-gaps.json` lists remaining abilities, declared hooks, ordinary probe outcomes and unresolved experiments.", "",
                 "| Catalog | Attempted | Declared outcomes | Smoke | Explained negative | Diagnose | Blocked |",
                 "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for kind in ("pokemon", "move", "ability"):
            subset = [row for row in catalog if row["kind"] == kind]
            counts = Counter(row["status"] for row in subset)
            values = [len(subset)] + [counts[name] for name in ("outcome_verified", "smoke_completed", "expected_failure", "needs_diagnosis", "blocked")]
            lines.append("| " + kind + " | " + " | ".join(map(str, values)) + " |")
        (self.output / "coverage-scope.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return summary


def main():
    """Build the honest scope index only when the live worker is not writing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    output = parser.parse_args().output.resolve()
    if not output.is_relative_to(pilot.ARTIFACTS) or output == pilot.ARTIFACTS:
        parser.error("Output must be an existing run folder inside .codex-artifacts.")
    with pilot.run_lock(output):
        print(json.dumps(CoverageIndex(output).build()))


if __name__ == "__main__":
    main()
