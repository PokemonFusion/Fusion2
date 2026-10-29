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
REPAIR_REPORTS = {
    853: "native-stat-items-2026-10-25.json",
    854: "legendary-item-identity-2026-10-25.json",
    855: "plate-theft-identity-2026-10-25.json",
    856: "memory-drive-theft-2026-10-25.json",
    857: "origin-primal-rusted-theft-2026-10-25.json",
    858: "held-status-berries-2026-10-25.json",
}


def current_registries():
    """Read explicit accepted source allowlists, never all catalog metadata."""
    from pokemon.battle.mega_pairs import MEGA_PAIRS
    from pokemon.battle.z_profiles import ZProfiles
    from pokemon.battle.z_generic_pairs import GENERIC_PAIRS
    from pokemon.battle.z_status_pairs import STATUS_PAIRS
    from pokemon.battle.z_signature_pairs import SIGNATURE_PAIRS
    from pokemon.battle.ultra_profile import UltraProfile

    profiles = (*ZProfiles.accepted.values(), *GENERIC_PAIRS, *STATUS_PAIRS, *SIGNATURE_PAIRS,
                UltraProfile.checked().z_profile())
    return MEGA_PAIRS, profiles


def repair_receipts():
    """Carry each dated proof's scope/status without upgrading it to live proof."""
    from pokemon.names import normalize_name

    result = []
    for issue, filename in REPAIR_REPORTS.items():
        path = ROOT / "docs/testing" / filename
        if not path.exists():
            result.append({"issue": issue, "status": "receipt_not_yet_published", "items": []})
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        if issue == 855:
            # Z-Crystals also carry onPlate metadata. The receipt's changed
            # callback list is the exact repaired inventory, not that metadata.
            names = report["changed_item_methods"]
        else:
            names = report.get("item_rules", report.get("items", []))
        result.append({"issue": issue, "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                       "sha256_lf": digest(path), "status": report["status"],
                       "evidence_kind": report.get("evidence_kind", "local automated; read exact receipt"),
                       "items": sorted({normalize_name(name) for name in names}),
                       "limit": "Only the named facets and sources in this dated receipt; no fresh live replay"})
    return result


def digest(path):
    """Use portable published-text identity across Windows/Git checkouts."""
    return hashlib.sha256(Path(path).read_text(encoding="utf-8").encode()).hexdigest()


def live_sources(snapshot, item_key):
    """Distinguish observed stock, disabled/empty stock and unknown live data."""
    from pokemon.names import normalize_name

    if snapshot is None:
        return {"status": "unverified", "sources": [], "limit": "No current world snapshot supplied"}
    sources, observed = [], []
    for obj in snapshot["world_objects"]:
        attrs = obj.get("attributes", {})
        stock = attrs.get("store_inventory")
        if isinstance(stock, dict):
            for name, data in stock.items():
                if normalize_name(name) == item_key and isinstance(data, dict):
                    quantity = data.get("quantity")
                    enabled = attrs.get("is_item_shop") is True
                    observed.append({"kind": "shop", "object_id": obj["id"], "enabled": enabled,
                                     "quantity": quantity})
                    if enabled and type(quantity) is int and quantity > 0:
                        sources.append({"kind": "configured_shop", "object_id": obj["id"],
                                        "name": obj["name"], "price": data.get("price"), "quantity": quantity})
        if normalize_name(attrs.get("dispense_item") or "") == item_key:
            stock = attrs.get("stock", "unknown")
            bundle = attrs.get("dispense_quantity", 1)
            bundle = max(1, bundle) if type(bundle) is int else 1
            observed.append({"kind": "vendor", "object_id": obj["id"], "stock": stock, "bundle": bundle})
            if stock is None or type(stock) is int and stock >= bundle:
                sources.append({"kind": "configured_vendor", "object_id": obj["id"], "name": obj["name"],
                                "location_id": obj.get("location"), "stock": stock,
                                "bundle": bundle})
    if sources:
        status = "configured_unverified_walkthrough"
    elif any((row["kind"] == "shop" and row["enabled"] and type(row["quantity"]) is int and row["quantity"] == 0)
             or (row["kind"] == "vendor" and type(row["stock"]) is int and 0 <= row["stock"] < row["bundle"])
             for row in observed):
        status = "observed_depleted_source"
    else:
        status = "observed_disabled_or_invalid_source" if observed else "no_observed_shop_or_vendor_source"
    return {"status": status, "sources": sources, "observed_sources": observed,
            "limit": "Snapshot does not prove reachability, locks, deployed effect or ordinary-player walkthrough"}


class ItemAvailabilityAudit:
    """Keep definition identity, supported commands and availability independent."""

    @staticmethod
    def z_profile_report(profile):
        """Associate only a specifically delivered crystal/source pair with its receipt."""
        from pokemon.names import normalize_name

        batches = {
            "z-next-six-sources-2026-10-29": (
                ("Firium Z", "Fire Blast"), ("Firium Z", "Flare Blitz"),
                ("Waterium Z", "Hydro Pump"), ("Electrium Z", "Thunder"),
                ("Groundium Z", "Earth Power"), ("Psychium Z", "Calm Mind")),
            "ultra-burst-2026-10-25": (("Ultranecrozium Z", "Photon Geyser"),),
            "z-existing-sources-2026-10-25": (("Firium Z", "Flamethrower"), ("Waterium Z", "Surf")),
            "z-six-special-sources-2026-10-25": (
                ("Electrium Z", "Thunderbolt"), ("Icium Z", "Ice Beam"),
                ("Grassium Z", "Energy Ball"), ("Psychium Z", "Psychic"),
                ("Ghostium Z", "Shadow Ball"), ("Poisonium Z", "Sludge Bomb")),
            "z-six-physical-sources-2026-10-25": (
                ("Normalium Z", "Body Slam"), ("Darkinium Z", "Crunch"),
                ("Dragonium Z", "Dragon Claw"), ("Groundium Z", "Earthquake"),
                ("Rockium Z", "Rock Slide"), ("Steelium Z", "Iron Head")),
            "z-six-status-sources-2026-10-25": (
                ("Normalium Z", "Recover"), ("Flyinium Z", "Roost"),
                ("Normalium Z", "Protect"), ("Poisonium Z", "Toxic"),
                ("Electrium Z", "Thunder Wave"), ("Grassium Z", "Synthesis")),
        }
        key = normalize_name(profile.crystal), normalize_name(profile.source)
        for report, pairs in batches.items():
            if key in {(normalize_name(item), normalize_name(source)) for item, source in pairs}:
                return report
        return "z-core-2026-10-23" if profile.kind == "generic" else "z-special-2026-10-23"

    def __init__(self, snapshot=None):
        """Accept only explicit primitive snapshot data; perform no ORM work."""
        self.snapshot = snapshot

    def build(self):
        """Account for every reviewed item and retain historical proof as historical."""
        from pokemon.data.evolution import required_item
        from pokemon.dex import ITEMDEX, POKEDEX
        from pokemon.items import GAMEPLAY_ITEMS, FIELD_TRAINING_ITEMS
        from pokemon.names import normalize_name
        from pokemon.services.battle_items import BattleMedicineUse
        from pokemon.services.field_abilities import FieldAbilityUse
        from pokemon.services.field_berries import FieldBerryUse
        from pokemon.services.field_food import FieldFoodUse
        from pokemon.services.field_hyper_training import FieldHyperTrainingUse
        from pokemon.services.field_items import FieldMedicineUse
        from pokemon.services.field_pp import FieldPPCapacityUse
        from pokemon.services.field_progression import FieldRareCandyUse
        from pokemon.services.exp_candy import FieldExpCandyUse
        from pokemon.services.field_mints import FieldMintUse
        from pokemon.battle.battle_boosters import BattleBoosters
        from pokemon.services.field_training import FieldTrainingUse
        from pokemon.services.field_recovery_equivalents import FieldRecoveryEquivalentUse
        from pokemon.services.item_supply import ItemSupplyRoute
        from pokemon.services.finite_item_supply import FINITE_SUPPLY_ROUTES
        from pokemon.services.berry_snack import BerrySnack
        from pokemon.services.berry_growing import BerryGrowing
        from pokemon.evolution_items import LinkCordEvolution
        from pokemon.services.itemfinder import FinderProfile

        matrix = json.loads((ROOT / MATRIX).read_text(encoding="utf-8"))
        historical = {normalize_name(row["item"]): row for row in matrix["items"]}
        definitions = {normalize_name(data.raw.get("name", data.name)): (data.raw.get("name", data.name), data.raw,
                       "pokemon/dex/items/itemsdex.py") for data in ITEMDEX.values()}
        for key, data in GAMEPLAY_ITEMS.items():
            definitions[key] = (data.name, data.raw, "pokemon/items.py")
        scoped = {key for key, row in historical.items() if not row.get("reason", "").startswith(EXCLUDED)}
        scoped.update(GAMEPLAY_ITEMS)
        excluded_cap = {key for key, (_, raw, _) in definitions.items() if raw.get("isNonstandard") == "CAP"}
        scoped.difference_update(excluded_cap)
        mega_pairs, z_profiles = current_registries()
        repairs = repair_receipts()
        recipes = []
        for filename in ("mega_stone_counter.json", "z_crystal_counter.json", "berry_nursery.json",
                         "berry_seed_counter.json", "ev_mochi_counter.json", "exp_candy_counter.json",
                         "battle_booster_counter.json", "nature_mint_counter.json",
                         "link_cord_counter.json", "chesto_seed_counter.json",
                         "contextual_evolution_counter.json", "soothe_bell_counter.json",
                         "npc_prize_item_counter.json"):
            path = ROOT / "world" / filename
            recipe = json.loads(path.read_text(encoding="utf-8"))
            recipes.append(("world/" + filename, recipe))
        for route in FINITE_SUPPLY_ROUTES.values():
            recipes.append(("pokemon/services/finite_item_supply.py", route.recipe()))
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
                    (FieldExpCandyUse, "exp", "exp-candy-2026-10-25"),
                    (FieldMintUse, "nature_training", "nature-mints-2026-10-25"),
                    (FieldRecoveryEquivalentUse, "field_recovery_equivalent", "item-followups-2026-10-22")]
        rows = []
        for key in sorted(scoped):
            name, raw, source = definitions[key]
            old = historical.get(key, {})
            field = [{"kind": kind, "command": "+use", "evidence_report":
                      "ev-mochi-2026-10-25" if key in FIELD_TRAINING_ITEMS else report}
                     for service, kind, report in services if service.supports(key)]
            routes, limits, followups = list(field), [], []
            if BattleBoosters.supports(key):
                routes.append({"kind": "battle_booster", "command": "+item [actor] <item>=<actor's party slot>",
                    "evidence_report": "battle-boosters-2026-10-25",
                    "limit": "Conscious current owned active self-target; two-participant wild/trainer/PvP single/double only; ability/Embargo/no-effect/copy/checkpoint guards; no field or held effect"})
            if BerrySnack.supports(key):
                routes.append({"kind": "berry_snack", "command": "+berry snack " + name + "=<target>",
                               "evidence_report": "berry-player-routes-2026-10-22" if key == "razzberry"
                               else "flavor-snacks-2026-10-25",
                               "limit": "PF2 up to 10 HP living field target; separate from +use/manual/held/growing"})
            if key in {normalize_name(seed) for seed in BerryGrowing.seeds}:
                routes.append({"kind": "berry_growing", "command": "+berry plant " + name + " / water / harvest",
                               "evidence_report": "training-grounds-delivery-2026-10-29"
                               if key in {"chestoberry", "sitrusberry", "lumberry"}
                               else "berry-player-routes-2026-10-22" if key == "oranberry" else "nursery-seeds-2026-10-25",
                               "limit": "One private bed at configured nursery; one bag seed, four real hours, yield 1-5; no automatic replant; real elapsed released acceptance is separate"})
            if key == "linkcord":
                routes.append({"kind": "link_cord_evolution", "command": "+evolve <full ID> Link Cord",
                    "mappings": list(LinkCordEvolution.transitions), "evidence_report": "link-cord-2026-10-29",
                    "limit": "One actual bag copy, exact native 14 mappings, regional/size preservation and independent bugs; held trade items unchanged"})
            if key in {"ovalstone", "razorclaw", "razorfang"}:
                routes.append({"kind": "contextual_held_evolution", "command": "+hold then daygrove/nightgrove then +evolve",
                    "evidence_report": "remaining-item-delivery-2026-10-29",
                    "limit": "Happiny/day, native Sneasel/night and Gligar/night; actual saved room and held copy. Other form/companion/context access remains world-unverified"})
            if key == "mirrorherb":
                routes.append({"kind": "daycare_egg_move_teaching", "command": "+daycare herb <recipient>=<donor>/<exact move>, then +daycare herb confirm",
                    "evidence_report": "remaining-item-delivery-2026-10-29",
                    "limit": "Configured Daycare, two eligible owned party members, exact Gen 9 native egg data, actual donor knowledge and empty slot; reusable, preserves old PP; public donor/item acquisition separate"})
            if key == "soothebell":
                routes.append({"kind": "field_friendship", "command": "+hold then +use <EV berry>=<target>",
                    "evidence_report": "remaining-item-delivery-2026-10-29",
                    "limit": "Six positive EV-berry friendship events only, floor 1.5x before cap; reusable, no loss/walking/level-up/battle friendship claim"})
            if key in {"amuletcoin", "luckincense"}:
                routes.append({"kind": "npc_prize", "command": "+hold then eligible standard NPC TRAINER participation and win",
                    "evidence_report": "remaining-item-delivery-2026-10-29",
                    "limit": "Saved genuine entry/action proof, maximum 2x once-only standard static/random prize receipt; excludes bench-only, PvP/Multi, wild, gym/Adventure/script, Pay Day and other currencies"})
            if key in {"cleansetag", "pureincense"}:
                limits.append("Hunt encounter reduction intentionally deferred by #938; no held encounter-rate effect claimed")
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
                pair = mega_pairs.get(key)
                if pair:
                    routes.append({"kind": "mega", "command": "+hold then +mega then +attack",
                                   "native": pair[0], "form": pair[1],
                                   "evidence_report": "mega-stones-2026-10-23",
                                   "limit": "Exact native pair only; current ownership/placement, suppression, form and side budget checks apply"})
                else:
                    limits.append("No accepted native Mega pair in the current registry")
            if raw.get("zMove") or raw.get("zMoveType"):
                profiles = [profile for profile in z_profiles if normalize_name(profile.crystal) == key]
                if profiles:
                    routes.append({"kind": "z_move", "command": ("+hold then +ultra/yes and +attack; later +zmove Photon Geyser=<target>"
                                   if key == "ultranecroziumz" else "+hold then +zmove <actual source slot>=<target>"),
                                   "profiles": [{"source": p.source, "result": p.name, "power": p.power,
                                                 "type": p.move_type, "category": "Attack-vs-SpA with raw stages; ties Special" if p.intrinsic == "ultra" else p.category, "target": p.target,
                                                 "kind": p.kind, "native": list(p.native), "intrinsic": p.intrinsic,
                                                 "bonus": list(p.bonus),
                                                 "evidence_report": self.z_profile_report(p)} for p in profiles],
                                   "evidence_report": "z-special-2026-10-23",
                                   "limit": "Only exact crystal/source mappings; native signatures, actual PP/held ownership, suppression, targets and side budget still apply"})
                    if raw.get("zMoveType"):
                        limits.append("Other source moves are deferred until an explicit mapping is qualified")
                        followups.append(864)
                    if key == "ultranecroziumz":
                        routes.append({"kind": "ultra_burst", "command": "+ultra [actor], yes, +attack; later +zmove Photon Geyser=<target>",
                                       "evidence_report": "ultra-burst-2026-10-25",
                                       "limit": "Exact live native pair/Photon/Prism Armor proof, independent Ultra budget, later-turn signature and current Photon PP/Z budget; category compares stored Attack/SpA with raw stages, ties Special"})
                        followups.append(888)
                else:
                    limits.append("Ultra Burst and Light That Burns the Sky have no accepted player lifecycle")
                    followups.append(865)
                if key in {"solganiumz", "lunaliumz"}:
                    routes.append({"kind": "native_necrozma_signature", "command": "+necrozma combine then +zmove",
                                   "evidence_report": "necrozma-items-2026-10-24",
                                   "released_local_report": "necrozma-released-retry-2026-10-24",
                                   "limit": "Valid live owned native pair proof only; Dusk-Mane/Sunsteel or Dawn-Wings/Moongeist; no Ultra or shared deployment claim"})
            if raw.get("isBerry") and not field and not BerrySnack.supports(key):
                limits.append("No field feeding route; a held trigger may be supported separately")
                if key in {normalize_name(name + " Berry") for name in
                           ("Bluk", "Nanab", "Pinap", "Wepear", "Cornn", "Magost", "Nomel", "Rabuta",
                            "Belue", "Durin", "Pamtre", "Spelon", "Watmel")}:
                    followups.append(866)
            if raw.get("isBerry") and key not in {normalize_name(seed) for seed in BerryGrowing.seeds}:
                limits.append("Growing accepts only " + ", ".join(BerryGrowing.seeds) + "; this berry is not an eligible seed")
            if field and not BattleMedicineUse.supports(key) and any(route["kind"] in {"berry", "food", "field_recovery_equivalent"} for route in field):
                limits.append("Intentionally excluded from manual battle use by the reviewed item policy; rejects before spending an action")
            authored = []
            for recipe_path, recipe in recipes:
                for offer in recipe.get("offers", []):
                    if normalize_name(offer["item"]) == key:
                        authored.append({"kind": "opt_in_recipe_shop", "source": recipe_path,
                                         "name": recipe["room"], "price": offer["price"],
                                         "initial_stock": offer["quantity"], "refill": recipe["refill"],
                                         "entry": recipe["entrance"],
                                         "limit": "Authored recipe only; installation, finite current stock, locks and reachability require separate world proof"})
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
            for training_name, weight in FinderProfile.training:
                if normalize_name(training_name) == key:
                    authored.append({"kind": "opt_in_training_finder", "source": "pokemon/services/item_activity_routes.py",
                        "entry": "trainingtrail", "profile": "training-v1", "find_percent": 5,
                        "conditional_weight_percent": weight, "quantity": 1,
                        "limit": "Supplementary named drop; one attempt per character per three seconds. Authored source is not installed stock or world acquisition"})
            if key in {"rarecandy", "bottlecap", "goldbottlecap"}:
                authored.append({"kind": "training_milestone", "source": "pokemon/services/training_grounds.py",
                    "useful_sessions": {"rarecandy": 6, "bottlecap": 12, "goldbottlecap": 60}[key],
                    "repeat": key != "goldbottlecap",
                    "limit": "Actual useful completed sessions only; resets/time alone grant none. Source requires explicitly configured Training Grounds; existing item-use eligibility remains"})
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
            rows[-1]["current_repair_evidence"] = [receipt for receipt in repairs if key in receipt["items"]]
        identity_paths = [MATRIX, "tools/audit_item_availability.py", "pokemon/battle/mega_pairs.py",
                          "pokemon/battle/z_profiles.py", "pokemon/battle/z_generic_pairs.py",
                          "pokemon/battle/z_status_pairs.py", "pokemon/battle/z_signature_pairs.py",
                          "pokemon/services/berry_snack.py", "pokemon/services/berry_growing.py",
                          "pokemon/evolution_items.py", "pokemon/services/evolution.py",
                          "pokemon/services/training_grounds.py", "pokemon/services/itemfinder.py",
                          "pokemon/services/item_activity_routes.py", "pokemon/field_friendship.py",
                          "pokemon/services/mirror_herb.py", "pokemon/mirror_herb.py",
                          "pokemon/services/daycare_teaching_location.py", "pokemon/battle/npc_prize_items.py",
                          "pokemon/battle/battle_boosters.py", "pokemon/battle/accuracy.py",
                          "pokemon/dex/functions/moves/damage_moves.py",
                          "pokemon/services/necrozma.py", "pokemon/battle/necrozma.py",
                          "pokemon/battle/ultra_profile.py", "pokemon/battle/ultra_eligibility.py",
                          "pokemon/battle/ultra_burst.py", "commands/player/cmd_battle_ultra.py",
                          "world/item_supply.json", *(path for path, _ in recipes)]
        identity_paths.extend(str(Path(sys.modules[service.__module__].__file__).relative_to(ROOT)).replace("\\", "/")
                              for service, _, _ in services)
        return {"schema_version": 2, "scope": "Non-plot evolution, recovery, berries/equivalents, training and held items; CAP/capture/TR/clutter excluded",
                "intentional_deferrals": [{"issue": 938, "items": ["Cleanse Tag", "Pure Incense"],
                    "status": "encounter_reduction_deferred",
                    "limit": "No new definition, source or encounter-rate effect is inferred from the scope decision"}],
                "definition_count": len(definitions), "scoped_count": len(rows),
                "excluded_cap": sorted(definitions[key][0] for key in excluded_cap),
                "current_registries": {"mega_pairs": len(mega_pairs), "z_mappings": len(z_profiles),
                                       "z_crystals": len({normalize_name(p.crystal) for p in z_profiles}),
                                       "z_kinds": dict(Counter(p.kind for p in z_profiles))},
                "repair_receipts": repairs,
                "native_necrozma": {"command": "+necrozma", "route": "Two real owned native base sources, Center review/confirm, reusable free combine/separate",
                                    "guide": "docs/necrozma.md", "evidence": "docs/testing/necrozma-items-2026-10-24.md",
                                    "released_local_evidence": "docs/testing/necrozma-released-retry-2026-10-24.md",
                                    "limit": "Local deliberately released build only; no Ultra or shared game deployment/obtainability claim"},
                "source_identities_sha256_lf": {path: digest(ROOT / path) for path in identity_paths},
                "counts": {"world_availability": dict(Counter(row["world_availability"]["status"] for row in rows)),
                           "support_status": dict(Counter(row["support_status"] for row in rows))},
                "world_snapshot": {key: self.snapshot.get(key) for key in ("observed_utc", "revision", "dirty", "transaction_read_only")}
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
