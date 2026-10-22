"""Build a non-plot item index without inferring acquisition from definitions.

This reads local sources and an optional, explicitly supplied read-only world
snapshot. It never connects to a game database, creates stock or grants items.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MATRIX = "docs/testing/battle-item-support-2026-10-21.json"
EXCLUDED = ("Capture-ball expansion", "TR/TM and incidental", "Collector/clutter")


def digest(path):
    """Use portable published-text identity across Windows/Git checkouts."""
    return hashlib.sha256(Path(path).read_text(encoding="utf-8").encode()).hexdigest()


def live_sources(snapshot, item_key):
    """Distinguish observed stock, disabled/empty stock and unknown live data."""
    from pokemon.names import normalize_name

    if snapshot is None:
        return {"status": "unverified", "sources": [], "limit": "No current world snapshot supplied"}
    sources = []
    for obj in snapshot["world_objects"]:
        attrs = obj.get("attributes", {})
        stock = attrs.get("store_inventory")
        if attrs.get("is_item_shop") is True and isinstance(stock, dict):
            for name, data in stock.items():
                if normalize_name(name) == item_key and isinstance(data, dict):
                    quantity = data.get("quantity")
                    if type(quantity) is int and quantity > 0:
                        sources.append({"kind": "configured_shop", "object_id": obj["id"],
                                        "name": obj["name"], "price": data.get("price"), "quantity": quantity})
        if normalize_name(attrs.get("dispense_item") or "") == item_key:
            stock = attrs.get("stock", "unknown")
            bundle = attrs.get("dispense_quantity", 1)
            bundle = max(1, bundle) if type(bundle) is int else 1
            if stock is None or type(stock) is int and stock >= bundle:
                sources.append({"kind": "configured_vendor", "object_id": obj["id"], "name": obj["name"],
                                "location_id": obj.get("location"), "stock": stock,
                                "bundle": bundle})
    return {"status": "configured_unverified_walkthrough" if sources else "no_observed_shop_or_vendor_source",
            "sources": sources,
            "limit": "Snapshot does not prove reachability, locks, deployed effect or ordinary-player walkthrough"}


class ItemAvailabilityAudit:
    """Keep definition identity, supported commands and availability independent."""

    def __init__(self, snapshot=None):
        """Accept only explicit primitive snapshot data; perform no ORM work."""
        self.snapshot = snapshot

    def build(self):
        """Account for every reviewed item and retain historical proof as historical."""
        from pokemon.data.evolution import required_item
        from pokemon.dex import ITEMDEX, POKEDEX
        from pokemon.items import GAMEPLAY_ITEMS
        from pokemon.names import normalize_name
        from pokemon.services.battle_items import BattleMedicineUse
        from pokemon.services.field_abilities import FieldAbilityUse
        from pokemon.services.field_berries import FieldBerryUse
        from pokemon.services.field_food import FieldFoodUse
        from pokemon.services.field_hyper_training import FieldHyperTrainingUse
        from pokemon.services.field_items import FieldMedicineUse
        from pokemon.services.field_pp import FieldPPCapacityUse
        from pokemon.services.field_progression import FieldRareCandyUse
        from pokemon.services.field_training import FieldTrainingUse
        from pokemon.services.field_recovery_equivalents import FieldRecoveryEquivalentUse
        from pokemon.services.item_supply import ItemSupplyRoute

        matrix = json.loads((ROOT / MATRIX).read_text(encoding="utf-8"))
        historical = {normalize_name(row["item"]): row for row in matrix["items"]}
        definitions = {normalize_name(data.raw.get("name", data.name)): (data.raw.get("name", data.name), data.raw,
                       "pokemon/dex/items/itemsdex.py") for data in ITEMDEX.values()}
        for key, data in GAMEPLAY_ITEMS.items():
            definitions[key] = (data.name, data.raw, "pokemon/items.py")
        scoped = {key for key, row in historical.items() if not row.get("reason", "").startswith(EXCLUDED)}
        scoped.update(GAMEPLAY_ITEMS)
        required = {normalize_name(required_item(species)) for species in POKEDEX.values() if required_item(species)}
        required.update({"blackaugurite", "peatblock", "scrollofdarkness", "scrollofwaters"})
        supply = {normalize_name(offer["item"]): offer for offer in ItemSupplyRoute.recipe()["offers"]}
        services = [(FieldMedicineUse, "medicine", "field-medicine-2026-10-20"),
                    (FieldBerryUse, "berry", "legacy-berries-2026-10-22"),
                    (FieldFoodUse, "food", "field-food-2026-10-21"),
                    (FieldTrainingUse, "training", "field-training-2026-10-22"),
                    (FieldAbilityUse, "ability", "ability-items-2026-10-22"),
                    (FieldHyperTrainingUse, "hyper_training", "hyper-training-2026-10-22"),
                    (FieldPPCapacityUse, "pp_capacity", "pp-capacity-2026-10-22"),
                    (FieldRareCandyUse, "level", "rare-candy-2026-10-22"),
                    (FieldRecoveryEquivalentUse, "field_recovery_equivalent", "item-followups-2026-10-22")]
        rows = []
        for key in sorted(scoped):
            name, raw, source = definitions[key]
            old = historical.get(key, {})
            field = [{"kind": kind, "command": "+use", "evidence_report": report}
                     for service, kind, report in services if service.supports(key)]
            routes, limits, followups = list(field), [], []
            if BattleMedicineUse.supports(key):
                routes.append({"kind": "manual_battle_medicine", "command": "+item",
                               "evidence_report": "battle-recovery-foods-2026-10-22"
                               if key not in BattleMedicineUse.standard_items else "battle-item-validation-2026-10-22",
                               "limit": "Named medicine only; owned roster target, effect and battle rules still apply"})
            if key in required:
                routes.append({"kind": "evolution", "command": "+evolve",
                               "limit": "Species, level, held/bag source and context conditions still apply"})
                if key == "gimmighoulcoin":
                    routes[-1].update(evidence_report="item-followups-2026-10-22",
                        limit="PF2 manual Chest Gimmighoul equivalent, level 2–100, exactly 999 bag coins; Roaming remains deferred")
            if key.endswith("sweet"):
                routes.append({"kind": "alcremie", "command": "+hold then +evolve", "limit": "Owned eligible Milcery; optional reviewed cream target"})
            if old.get("scope") == "retained":
                routes.append({"kind": "held_or_battle", "command": "See exact historical facet; +item is limited to medicine",
                               "status": "historical_context_verified", "batches": old["batches"]})
            if key.endswith("incense") and key in {"oddincense", "rockincense", "roseincense", "seaincense", "waveincense"}:
                routes.append({"kind": "held_booster", "command": "+hold then +attack", "evidence_report": "incense-2026-10-22"})
            if key == "smokeball":
                routes.append({"kind": "held_escape", "command": "+hold then +flee", "evidence_report": "smoke-ball-2026-10-21"})
            if key == "everstone":
                routes.append({"kind": "evolution_block", "command": "+hold blocks +evolve", "limit": "Return it with +hold <slot>= before evolving"})
            if key == "leaderscrest":
                routes.append({"kind": "opponent_qualification", "command": "+hunt / +challenge then +evolve",
                               "limit": "Defeat three authored Crest Bisharp; player does not obtain or consume a Crest"})
            if raw.get("megaStone"):
                limits.append("No supported ordinary player Mega activation slice")
                followups.append(774)
            if raw.get("zMove") or raw.get("zMoveType"):
                limits.append("No supported ordinary player Z activation slice")
                followups.append(775)
            if raw.get("isBerry") and not field:
                limits.append("No field feeding/growing route; a held trigger may be supported separately")
                followups.append(776)
            if field and not BattleMedicineUse.supports(key) and any(route["kind"] in {"berry", "food", "field_recovery_equivalent"} for route in field):
                limits.append("Intentionally excluded from manual battle use by the reviewed item policy; rejects before spending an action")
            authored = []
            if key in supply:
                offer = supply[key]
                authored.append({"kind": "opt_in_recipe_shop", "source": "world/item_supply.json",
                    "name": "Item Supply Corner", "price": offer["price"], "initial_stock": offer["quantity"],
                    "refill": "none", "entry": "supplies at the explicitly configured public hub",
                    "limit": "Recipe is not automatically installed or live stock; current-world reachability/stock remains separately verified"})
            if key == "potion":
                authored.append({"kind": "opt_in_itemfinder", "source": "pokemon/services/itemfinder.py",
                    "item": "Potion", "quantity": 1, "reference_rate_percent": 5,
                    "limit": "Requires reviewed named room source, enabled hunting and noitem false; no world population inferred"})
            if key == "oranberry":
                authored.append({"kind": "opt_in_wild_held", "source": "pokemon/services/wild_held_items.py",
                    "species": "Rattata", "reference_chance_percent": 5,
                    "limit": "Explicit held_item/held_item_chance chart; noitem still applies; capture retains current uneaten item only"})
            if key in {"gimmighoulcoin", "ragecandybar", "hopoberry"}:
                authored.append({"kind": "documented_reference_shop", "source": "docs/gimmighoul-evolution.md"
                    if key == "gimmighoulcoin" else "docs/recovery-equivalents.md",
                    "limit": "Deliberate optional reference recipe only; no installed location, current stock or live walkthrough inferred"})
            if key == "rarecandy":
                authored.append({"kind": "alpha_recipe_vendor", "source": "world/alpha_test_zone.ev",
                                 "name": "Alpha Candy Dispenser", "command": "+vend Alpha Candy Dispenser 1",
                                 "limit": "Recipe must be deliberately built; absent in inspected remote snapshot"})
            if key == "potion":
                authored.append({"kind": "adventure_first_clear", "source": "pokemon/adventures/templates.py",
                                 "template": "alpha_meadow", "quantity": 1, "command": "+adventure / +adventure/claim",
                                 "limit": "Once per character; live reachability/completion not walked in this audit"})
            live = live_sources(self.snapshot, key)
            if not authored and not live["sources"]:
                limits.append("No specific authored shop/vendor/reward source found in reviewed sources/snapshot")
            rows.append({"item": name, "key": key, "definition_source": source,
                         "definition_sha256": hashlib.sha256(json.dumps(raw, sort_keys=True, default=str).encode()).hexdigest(),
                         "routes": routes, "authored_acquisition": authored, "world_availability": live,
                         "support_status": "deferred" if followups and not routes else "capability_with_bounded_evidence" if routes else "unverified",
                         "limits": limits, "followups": sorted(set(followups)),
                         "historical_evidence": old.get("evidence", []), "historical_batches": old.get("batches", [])})
        return {"schema_version": 1, "scope": "Non-plot evolution, recovery, berries/equivalents, training and held items; capture/TR/clutter excluded",
                "definition_count": len(definitions), "scoped_count": len(rows),
                "counts": {"world_availability": dict(Counter(row["world_availability"]["status"] for row in rows)),
                           "support_status": dict(Counter(row["support_status"] for row in rows))},
                "world_snapshot": {key: self.snapshot[key] for key in ("observed_utc", "revision", "dirty", "transaction_read_only")}
                                  if self.snapshot else None,
                "items": rows, "historical_matrix": {"path": MATRIX, "sha256_lf": digest(ROOT / MATRIX),
                                                     "status": "historical_observations_not_a_fresh_replay"}}


def main():
    """Write or summarize the offline index, with optional explicit world data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8")) if args.snapshot else None
    result = ItemAvailabilityAudit(snapshot).build()
    if args.output:
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("definition_count", "scoped_count", "counts")}))


if __name__ == "__main__":
    main()
