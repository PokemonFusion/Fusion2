"""Keep support claims tied to complete inventory and concrete retained proof."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from reconcile_item_support import ItemSupportReconciler, MATRIX, text_digest


def test_checked_in_matrix_accounts_for_the_dex_and_freezes_bounded_lists():
    matrix = ItemSupportReconciler().build()
    assert matrix == json.loads(MATRIX.read_text(encoding="utf-8"))
    rows = matrix["items"]
    assert all(row.get("evidence") or row.get("reason") for row in rows)
    for batch in matrix["batches"]:
        assert batch["budget"]["items"] == len(batch["items"]) <= 25
        assert batch["budget"]["battle_templates"] <= 50
        assert batch["budget"]["new_checks"] == 0
    checks = [check for batch in matrix["batches"] if batch["family"] != "rewards" for check in batch["checks"]]
    assert len(checks) == len(set(checks)) == matrix["summary"]["verified_pvp_checks"]
    assert all(row["batches"] for row in rows if row["scope"] == "retained")


@pytest.mark.parametrize("mutation, message", [
    ("duplicate", "Duplicate inventory"),
    ("missing", "Dex inventory changed"),
    ("failed", "Unresolved declared effects"),
    ("empty", "Effect has no normal-flow evidence"),
    ("no_rationale", "Excluded item lacks a rationale"),
    ("unknown_family", "Unplanned effect family"),
])
def test_reconciliation_rejects_unjustified_support_claims(mutation, message):
    reconciler = ItemSupportReconciler()
    if mutation == "duplicate":
        reconciler.data["item_matrix"].append(reconciler.data["item_matrix"][0])
    elif mutation == "missing":
        reconciler.data["item_matrix"].pop()
    elif mutation == "failed":
        reconciler.data["item_evidence_audit"]["facets"][0]["status"] = "needs_diagnosis"
    elif mutation == "empty":
        reconciler.data["item_evidence_audit"]["facets"][0]["cases"] = []
    elif mutation == "no_rationale":
        next(row for row in reconciler.data["item_matrix"] if row["scope"] == "excluded")["reason"] = ""
    elif mutation == "unknown_family":
        reconciler.data["item_evidence_audit"]["facets"][0]["group"] = "unplanned"
    with pytest.raises(AssertionError, match=message):
        reconciler.build()


def test_altered_archive_cannot_reuse_historical_verification(tmp_path):
    reconciler = ItemSupportReconciler()
    first = reconciler.data["item_evidence_audit"]["facets"][0]["cases"][0]
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / (first["key"] + ".json.gz")).write_bytes(b"changed")
    with pytest.raises(AssertionError, match="Archive changed"):
        reconciler.verify_archives(tmp_path)


def test_published_text_identity_survives_git_checkout_newline_conversion(tmp_path):
    first, second = tmp_path / "lf.json", tmp_path / "crlf.json"
    first.write_bytes(b'{"item": "Oran Berry"}\n')
    second.write_bytes(b'{"item": "Oran Berry"}\r\n')
    assert text_digest(first) == text_digest(second)
