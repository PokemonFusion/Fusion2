"""Reconcile bounded held-item proof without rewriting historical observations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "docs/testing/full-battle-postformfix-2026-10-20.json"
MATRIX = REPO / "docs/testing/battle-item-support-2026-10-21.json"

FAMILIES = {
    "stat-type": {
        "type-power", "stat-offense", "stat-defense", "stat-modifiers",
        "species-power", "power", "signature-type", "weight", "repeat-power", "critical",
    },
    "hit-consumable": {
        "berries", "berry-flavor", "berry-heal", "berry-pp", "berry-stat", "berry-status",
        "natural-gift", "charge", "copy-boost", "damage-healing", "field-trigger",
        "gem-damage", "gem-negative", "gems", "hit-trigger", "recoil-negative",
        "residual", "resistance", "survival", "survival-negative", "sustain", "threshold-trigger",
    },
    "accuracy-priority": {
        "accuracy", "accuracy-miss", "accuracy-negative", "choice-lock",
        "choice-restriction", "flinch", "multihit", "turn-order",
    },
    "field-trapping": {
        "contact-prevention", "effect-prevention", "field-duration", "full-lifetime",
        "hazard-prevention", "holder-weather", "immunity", "protection",
        "suppression-negative", "switching", "trapping", "volatile-reflection",
    },
    "identity-form": {"evolution-negative", "native-ability", "native-form"},
    "medicine-protocol": {"medicine", "medicine-negative", "medicine-targeting", "repair-protocol"},
}


def digest(path):
    """Hash exact retained bytes, including compressed evidence archives."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(path):
    """Identify published text independent of Git checkout newline conversion."""
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


class ItemSupportReconciler:
    """Require complete inventory accounting and independently audited effect rows."""

    max_items = 25
    max_cases = 50

    def __init__(self, report=REPORT):
        self.report = Path(report)
        self.data = json.loads(self.report.read_text(encoding="utf-8"))

    def build(self):
        """Produce per-item pointers and finite rerun budgets from final observations."""
        from pokemon import dex
        from tools.qa.live_dex_cases import unique_entries

        inventory = {name for name, _ in unique_entries(dex.ITEMDEX)}
        rows = self.data["item_matrix"]
        assert len(rows) == len({row["item"] for row in rows}), "Duplicate inventory rows"
        assert {row["item"] for row in rows} == inventory, "Dex inventory changed; reconcile scope explicitly"
        audit = self.data["item_evidence_audit"]
        assert not audit["errors"], "Unresolved evidence audit errors"
        facets = audit["facets"]
        assert len(facets) == len({f["label"] for f in facets}), "Duplicate effect labels"
        assert all(f["status"] == "outcome_verified" for f in facets), "Unresolved declared effects"
        assert all(f["cases"] for f in facets), "Effect has no normal-flow evidence"
        assert all(len(c["sha256"]) == 64 for f in facets for c in f["cases"]), "Missing evidence checksum"
        families = {group: family for family, groups in FAMILIES.items() for group in groups}
        assert {f["group"] for f in facets} <= families.keys(), "Unplanned effect family"
        by_label = {f["label"]: index for index, f in enumerate(facets)}
        batches = []
        for family in FAMILIES:
            selected = [f for f in facets if families[f["group"]] == family]
            pending, items, cases = [], [], set()

            def flush():
                """Freeze the exact list; new behavior needs its own bounded issue."""
                if pending:
                    batches.append({
                        "id": family + "-" + str(1 + sum(b["family"] == family for b in batches)),
                        "family": family, "items": list(items),
                        "checks": [f["label"] for f in pending], "case_keys": sorted(cases),
                        "budget": {"items": len(items), "effect_checks": len(pending),
                                   "battle_templates": len(cases), "new_checks": 0},
                        "status": "historical_declared_effects_verified",
                    })

            for item in sorted({f["item"] for f in selected}):
                additions = [f for f in selected if f["item"] == item]
                extra_cases = {c["key"] for f in additions for c in f["cases"]}
                if pending and (len(items) == self.max_items or len(cases | extra_cases) > self.max_cases):
                    flush()
                    pending, items, cases = [], [], set()
                assert len(extra_cases) <= self.max_cases, "Item needs a separately bounded plan"
                pending.extend(additions)
                items.append(item)
                cases.update(extra_cases)
            flush()

        retained, excluded, items = [], [], []
        for row in rows:
            item = row["item"]
            if row["scope"] == "excluded":
                assert row.get("reason") and row["status"] == "out_of_scope", "Excluded item lacks a rationale"
                excluded.append(item)
                items.append(dict(row))
                continue
            assert row["scope"] == "retained", "Unclassified inventory row"
            assert row["status"] == "declared_actual_effects_verified_in_tested_context"
            evidence = []
            for label in row["checks"]:
                index = by_label[label]
                assert facets[index]["item"] == item, "Effect belongs to another item"
                evidence.append({"label": label, "pointer": "#/item_evidence_audit/facets/" + str(index),
                                 "cases": facets[index]["cases"]})
            if row.get("reward"):
                reward = row["reward"]
                assert reward["status"] == "outcome_verified"
                index = self.data["reward_checks"].index(reward)
                evidence.append({"label": reward["evidence"], "pointer": "#/reward_checks/" + str(index),
                                 "sha256": reward["evidence_sha256"]})
            for index, result in enumerate(self.data["forced_form_eligibility_results"]):
                if result["held_item"] == item:
                    assert result["status"] == "outcome_verified", "Unresolved form eligibility check"
                    evidence.append({"label": result["key"],
                                     "pointer": "#/forced_form_eligibility_results/" + str(index),
                                     "sha256": result["sha256"]})
            assert evidence, "Retained item lacks normal-flow proof: " + item
            retained.append(item)
            items.append({"item": item, "scope": "retained", "status": "historical_declared_effects_verified",
                          "batches": [b["id"] for b in batches if item in b["items"]],
                          "evidence": evidence, "limits": "Only the declared tested contexts; see report boundaries."})

        assert {f["label"] for f in facets} == {label for row in rows for label in row.get("checks", [])}
        rewards = [r for r in self.data["reward_checks"] if r["item"]]
        assert all(r["status"] == "outcome_verified" for r in rewards)
        batches.append({"id": "rewards-1", "family": "rewards", "items": sorted(r["item"] for r in rewards),
                        "checks": [r["evidence"] for r in self.data["reward_checks"]],
                        "budget": {"items": len(rewards), "effect_checks": len(rewards),
                                   "battle_templates": len(rewards) + 1, "new_checks": 0},
                        "status": "historical_declared_effects_verified"})
        for row in items:
            if row["item"] in batches[-1]["items"]:
                row["batches"].append("rewards-1")
        return {
            "scope": "Existing in-policy battle/reward items only; plot-only, field evolution and additions excluded.",
            "source_report": self.report.relative_to(REPO).as_posix(),
            "source_report_sha256_lf": text_digest(self.report),
            "historical_source_commit": self.data["source_commit"],
            "historical_build_note": self.data["build_note"],
            "summary": {"loaded_definitions": len(inventory), "retained_items": len(retained),
                        "excluded_definitions": len(excluded), "verified_pvp_checks": len(facets),
                        "pvp_case_templates": len({c["key"] for f in facets for c in f["cases"]}),
                        "verified_reward_checks": len(rewards), "bounded_batches": len(batches)},
            "evidence_boundaries": {
                "historical_local_player": "Final 2026-10-20 localhost ordinary-player sweep; exact report and archive hashes retained.",
                "fresh_automated": "See item-support-closeout-2026-10-21.md for current fixture/core/gate results.",
                "merged": "Prior repairs published on staging; this matrix is not evidence of a main-branch merge.",
                "deployed": "No remote deployment or fresh live-player acceptance performed for this reconciliation.",
                "unsupported": "Excluded definitions, progression/acquisition, full Mega/Z and untested combinations remain separate.",
                "help": "#731 owns player guidance; no command/help availability changes in this reconciliation.",
            },
            "batch_policy": {"max_items": self.max_items, "max_battle_templates": self.max_cases,
                             "expansion": "Freeze these lists before rerun; file unrelated defects as separate bounded issues."},
            "batches": batches, "items": items,
        }

    def compare_runtime_source(self):
        """Report local raw-byte drift separately from the portable support matrix."""
        current, changed = {}, []
        for name, pinned in self.data["source_files_sha256"].items():
            if (name.startswith(("pokemon/battle/", "pokemon/dex/", "pokemon/helpers/", "pokemon/services/"))
                    and "/tests/" not in name and name.endswith(".py")):
                actual = digest(REPO / name)
                current[name] = actual
                if actual != pinned:
                    changed.append(name)
        return {"current_sha256": current, "changed_since_historical_sweep": changed,
                "claim": "Local byte comparison includes checkout newlines; historical observations are not a fresh run."}

    def verify_archives(self, root):
        """Rehash final case archives read-only; never run saved staff/setup scripts."""
        root = Path(root)
        expected = {}
        for facet in self.data["item_evidence_audit"]["facets"]:
            for case in facet["cases"]:
                previous = expected.setdefault(case["key"], case["sha256"])
                assert previous == case["sha256"], "Conflicting case checksums"
        for key, sha256 in expected.items():
            assert digest(root / "evidence" / (key + ".json.gz")) == sha256, "Archive changed: " + key
        for row in self.data["reward_checks"]:
            assert digest(root / "evidence" / (row["evidence"] + ".json.gz")) == row["evidence_sha256"], "Reward archive changed"
        return {"pvp_archives": len(expected), "reward_archives": len(self.data["reward_checks"]), "errors": []}


def main():
    """Write or check the current reconciliation, optionally rehash local evidence."""
    sys.path.insert(0, str(REPO))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--compare-local-source", action="store_true")
    args = parser.parse_args()
    reconciler = ItemSupportReconciler()
    matrix = reconciler.build()
    encoded = json.dumps(matrix, indent=2, ensure_ascii=True) + "\n"
    if args.check:
        assert MATRIX.read_text(encoding="utf-8") == encoded, "Checked-in matrix is stale"
    else:
        MATRIX.write_text(encoded, encoding="utf-8")
    result = {"summary": matrix["summary"]}
    if args.evidence_root:
        result["archives"] = reconciler.verify_archives(args.evidence_root)
    if args.compare_local_source:
        comparison = reconciler.compare_runtime_source()
        result["runtime_source_comparison"] = {"pinned_files_checked": len(comparison["current_sha256"]),
                                              "changed": comparison["changed_since_historical_sweep"],
                                              "claim": comparison["claim"]}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
