"""Coverage inventory for offline battle outcome proofs."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from pokemon.battle.tests.outcome_harness import coverage_id, normalize_key
from tests.battle_contract_catalog import ALL_CONTRACTS


EXPLICIT_CONTRACT = "explicit_contract"
MECHANIC_CONTRACT = "mechanic_contract"
SMOKE_ONLY = "smoke_only"
KNOWN_GAP = "known_gap"

COVERAGE_STATUSES = (EXPLICIT_CONTRACT, MECHANIC_CONTRACT, SMOKE_ONLY, KNOWN_GAP)

KNOWN_GAPS: dict[str, str] = {}


@dataclass(frozen=True)
class CoverageRecord:
    """One dex entry's relationship to offline proof coverage."""

    kind: str
    name: str
    subject: str
    status: str
    mechanics: tuple[str, ...]
    contracts: tuple[str, ...] = ()
    reason: str = ""


def supported_mechanics() -> frozenset[str]:
    """Return mechanic groups with at least one executable semantic contract."""

    return frozenset(contract.mechanic for contract in ALL_CONTRACTS if contract.mechanic)


SUPPORTED_MECHANICS = supported_mechanics()


def normalize_subject(subject: str) -> str:
    """Normalize ``kind:name`` coverage ids into stable dex keys."""

    if ":" not in subject:
        return normalize_key(subject)
    kind, name = subject.split(":", 1)
    return coverage_id(kind, name)


def contracts_by_subject() -> dict[str, tuple[str, ...]]:
    """Map coverage subject ids to contract names proving them directly."""

    grouped: dict[str, list[str]] = defaultdict(list)
    for contract in ALL_CONTRACTS:
        for subject in getattr(contract, "covers", ()) or ():
            grouped[normalize_subject(subject)].append(contract.name)
    return {subject: tuple(names) for subject, names in grouped.items()}


CONTRACTS_BY_SUBJECT = contracts_by_subject()


def entry_name(key: str, entry: Any) -> str:
    return str(getattr(entry, "name", None) or key)


def entry_raw(entry: Any) -> Mapping[str, Any]:
    raw = getattr(entry, "raw", None)
    if isinstance(raw, Mapping):
        return raw
    if isinstance(entry, Mapping):
        return entry
    return {}


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iter_effects(raw: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield direct, self, and secondary effect dictionaries from move raw data."""

    yield raw
    self_effect = raw.get("self")
    if isinstance(self_effect, Mapping):
        yield self_effect

    secondary = raw.get("secondary")
    if isinstance(secondary, Mapping):
        yield secondary

    secondaries = raw.get("secondaries") or ()
    if isinstance(secondaries, Mapping):
        yield secondaries
    else:
        for effect in secondaries:
            if isinstance(effect, Mapping):
                yield effect
                nested_self = effect.get("self")
                if isinstance(nested_self, Mapping):
                    yield nested_self


def _has_callback(raw: Mapping[str, Any]) -> bool:
    return any(str(key).startswith("on") or str(key).endswith("Callback") for key in raw)


def _has_percent_branch(raw: Mapping[str, Any]) -> bool:
    accuracy = _numeric(raw.get("accuracy"))
    if accuracy is not None and accuracy < 100:
        return True
    for effect in _iter_effects(raw):
        chance = _numeric(effect.get("chance"))
        if chance is not None and chance < 100:
            return True
        status_chance = _numeric(effect.get("statusChance"))
        if status_chance is not None and status_chance < 100:
            return True
    return False


def infer_move_mechanics(raw: Mapping[str, Any]) -> tuple[str, ...]:
    """Infer mechanic groups used by a move from Showdown-style raw data."""

    mechanics: set[str] = set()
    category = str(raw.get("category", "") or "").lower()
    base_power = _numeric(raw.get("basePower"))
    if category != "status" and base_power is not None and base_power > 0:
        mechanics.add("damage")
    if category != "status" and "damage" in raw:
        mechanics.add("fixed_damage")

    if raw.get("secondary") or raw.get("secondaries"):
        mechanics.add("secondary_effect")

    for effect in _iter_effects(raw):
        if effect.get("status"):
            mechanics.add("status_outcome")
        if effect.get("boosts"):
            mechanics.add("stat_boost")
        if effect.get("heal"):
            mechanics.add("healing")
        if effect.get("drain"):
            mechanics.add("drain")
        if effect.get("recoil"):
            mechanics.add("recoil")
        if effect.get("volatileStatus"):
            mechanics.add("volatile")

    if raw.get("weather"):
        mechanics.add("weather")
    if raw.get("terrain"):
        mechanics.add("terrain")
    condition = raw.get("condition")
    if isinstance(condition, Mapping) and any(str(key).startswith("onField") for key in condition):
        mechanics.add("field_condition")
    if raw.get("sideCondition") or raw.get("slotCondition"):
        mechanics.add("side_condition")
    if raw.get("forceSwitch"):
        mechanics.add("forced_switch")
    if raw.get("selfSwitch"):
        mechanics.add("self_switch")

    priority = _numeric(raw.get("priority"))
    if priority is not None and priority != 0:
        mechanics.add("priority")
    if _has_percent_branch(raw):
        mechanics.add("random_branch")
    if raw.get("basePowerCallback") or raw.get("damageCallback") or raw.get("onBasePower"):
        mechanics.add("callback_damage")
    combo_names = {
        "firepledge",
        "waterpledge",
        "grasspledge",
        "round",
        "fusionbolt",
        "fusionflare",
    }
    if normalize_key(raw.get("name")) in combo_names or raw.get("sourceEffect"):
        mechanics.add("combo_move")
    if _has_callback(raw):
        mechanics.add("callback_behavior")
    return tuple(sorted(mechanics))


def infer_ability_mechanics(raw: Mapping[str, Any]) -> tuple[str, ...]:
    """Infer mechanic groups used by an ability from raw callback keys."""

    mechanics: set[str] = set()
    named_mechanics = {
        "noability": "no_battle_effect",
        "ballfetch": "ability_post_battle_item",
        "corrosion": "ability_status_bypass",
        "dancer": "ability_dance_copy",
        "earlybird": "ability_sleep_modifier",
        "honeygather": "ability_post_battle_item",
        "levitate": "ability_ground_immunity",
        "multitype": "ability_flag_protection",
        "rkssystem": "ability_flag_protection",
        "runaway": "ability_escape",
        "persistent": "ability_field_duration",
    }
    named = named_mechanics.get(normalize_key(raw.get("name")))
    if named:
        mechanics.add(named)
    immunity_hooks = {
        "onTryHit",
        "onTryHitSide",
        "onAllyTryHitSide",
        "onSetStatus",
        "onTryAddVolatile",
        "onAllySetStatus",
        "onAllyTryAddVolatile",
    }
    damage_modifier_hooks = {
        "onModifyAtk",
        "onModifySpA",
        "onModifyDef",
        "onModifySpD",
        "onModifySpe",
        "onSourceModifyAtk",
        "onSourceModifySpA",
        "onAnyModifyAtk",
        "onAnyModifyDef",
        "onAnyModifySpA",
        "onAnyModifySpD",
        "onBasePower",
        "onAllyBasePower",
        "onAnyBasePower",
        "onSourceBasePower",
        "onModifySTAB",
        "onDamage",
        "onModifyDamage",
        "onSourceModifyDamage",
    }
    move_modifier_hooks = {
        "onModifyMove",
        "onModifyType",
        "onModifyPriority",
        "onFractionalPriority",
        "onModifyAccuracy",
        "onSourceModifyAccuracy",
        "onAnyModifyAccuracy",
        "onModifyCritRatio",
        "onPrepareHit",
        "onCriticalHit",
        "onModifyWeight",
        "onEffectiveness",
    }
    contact_trigger_hooks = {
        "onDamagingHit",
        "onSourceDamagingHit",
        "onAfterMoveSecondary",
        "onAfterMoveSecondarySelf",
    }
    boost_guard_hooks = {
        "onTryBoost",
        "onChangeBoost",
        "onAfterEachBoost",
        "onAfterBoost",
    }
    weather_hooks = {
        "onWeather",
        "onWeatherChange",
        "onTerrainChange",
        "onAnySetWeather",
        "onAnySetTerrain",
    }
    weather_ability_names = {
        "airlock",
        "cloudnine",
        "deltastream",
        "desolateland",
        "drizzle",
        "drought",
        "electricsurge",
        "grassysurge",
        "hadronengine",
        "mistysurge",
        "orichalcumpulse",
        "primordialsea",
        "psychicsurge",
        "sandstream",
        "snowwarning",
    }
    item_trigger_hooks = {
        "onEatItem",
        "onTryEatItem",
        "onFoeTryEatItem",
        "onAfterUseItem",
        "onAllyAfterUseItem",
        "onTakeItem",
    }
    faint_trigger_hooks = {
        "onFaint",
        "onSourceAfterFaint",
        "onAllyFaint",
    }
    control_hooks = {
        "onFoeTryMove",
        "onBeforeMove",
        "onAnyRedirectTarget",
        "onDragOut",
        "onFoeTrapPokemon",
        "onFoeMaybeTrapPokemon",
        "onTrapPokemon",
    }
    if any(hook in raw for hook in immunity_hooks):
        mechanics.add("ability_immunity")
    if "onResidual" in raw:
        mechanics.add("ability_residual")
    if any(hook in raw for hook in ("onPreStart", "onStart", "onSwitchIn")):
        mechanics.add("ability_start")
    if any(hook in raw for hook in damage_modifier_hooks):
        mechanics.add("ability_damage_modifier")
    if any(hook in raw for hook in move_modifier_hooks):
        mechanics.add("ability_move_modifier")
    if any(hook in raw for hook in contact_trigger_hooks):
        mechanics.add("ability_contact_trigger")
    if any(hook in raw for hook in boost_guard_hooks):
        mechanics.add("ability_boost_guard")
    if any(hook in raw for hook in weather_hooks) or normalize_key(raw.get("name")) in weather_ability_names:
        mechanics.add("ability_weather")
    if any(hook in raw for hook in item_trigger_hooks):
        mechanics.add("ability_item_trigger")
    if any(hook in raw for hook in faint_trigger_hooks):
        mechanics.add("ability_faint_trigger")
    if any(hook in raw for hook in control_hooks):
        mechanics.add("ability_control")
    if _has_callback(raw):
        mechanics.add("callback_behavior")
    return tuple(sorted(mechanics))


def infer_item_mechanics(raw: Mapping[str, Any]) -> tuple[str, ...]:
    """Infer mechanic groups used by a held item from raw callback keys."""

    mechanics: set[str] = set()
    name_key = normalize_key(raw.get("name"))
    has_callback = _has_callback(raw)

    healing_berries = {
        "aguavberry",
        "berryjuice",
        "enigmaberry",
        "figyberry",
        "iapapaberry",
        "magoberry",
        "oranberry",
        "sitrusberry",
        "wikiberry",
    }
    status_berries = {
        "aspearberry",
        "cheriberry",
        "chestoberry",
        "lumberry",
        "pechaberry",
        "persimberry",
        "rawstberry",
        "bitterberry",
        "burntberry",
        "iceberry",
        "mintberry",
        "miracleberry",
        "przcureberry",
        "psncureberry",
    }
    stat_berries = {
        "apicotberry",
        "ganlonberry",
        "keeberry",
        "lansatberry",
        "liechiberry",
        "marangaberry",
        "micleberry",
        "petayaberry",
        "salacberry",
        "starfberry",
    }
    terrain_seed_items = {
        "electricseed",
        "grassyseed",
        "mistyseed",
        "psychicseed",
    }
    choice_items = {
        "choiceband",
        "choicescarf",
        "choicespecs",
    }
    bag_use_items = {
        "antidote",
        "awakening",
        "burnheal",
        "fullheal",
        "fullrestore",
        "hyperpotion",
        "iceheal",
        "maxpotion",
        "paralyzeheal",
        "potion",
        "superpotion",
    }

    if "onResidual" in raw:
        mechanics.add("item_residual")
    if "onBasePower" in raw:
        mechanics.add("item_base_power")
    if any(
        hook in raw
        for hook in (
            "onModifyAtk",
            "onModifyDef",
            "onModifySpA",
            "onModifySpD",
            "onModifySpe",
            "onModifyWeight",
        )
    ):
        mechanics.add("item_stat_modifier")
    if any(hook in raw for hook in ("onModifyAccuracy", "onSourceModifyAccuracy")):
        mechanics.add("item_accuracy_modifier")
    if "onModifyCritRatio" in raw:
        mechanics.add("item_crit_modifier")
    if "onModifySecondaries" in raw:
        mechanics.add("item_secondary_guard")
    if "onAttract" in raw:
        mechanics.add("item_volatile_reflect")
    if "onModifyExp" in raw:
        mechanics.add("item_exp_modifier")
    if "onFoeAfterBoost" in raw:
        mechanics.add("item_boost_copy")
    if "onChargeMove" in raw:
        mechanics.add("item_charge_skip")
    if "onNegateImmunity" in raw:
        mechanics.add("item_immunity_modifier")
    if any(hook in raw for hook in ("onImmunity", "onTryHit")):
        mechanics.add("item_immunity_guard")
    if any(hook in raw for hook in ("onModifyDamage", "onSourceModifyDamage")):
        if raw.get("isBerry") and "onSourceModifyDamage" in raw:
            mechanics.add("item_resist_berry")
        else:
            mechanics.add("item_damage_modifier")
    if "onSourceTryPrimaryHit" in raw:
        mechanics.add("item_gem_trigger")
    if any(
        hook in raw
        for hook in (
            "onAfterMoveSecondary",
            "onAfterMoveSecondarySelf",
            "onAfterSubDamage",
            "onDamagingHit",
            "onHit",
        )
    ):
        mechanics.add("item_hit_trigger")
    if "onDamage" in raw:
        mechanics.add("item_damage_survival")
    if "onTryHeal" in raw:
        mechanics.add("item_heal_modifier")
    if any(hook in raw for hook in ("onDisableMove", "onModifyMove")):
        if raw.get("isChoice") or name_key in choice_items:
            mechanics.add("item_choice_lock")
        else:
            mechanics.add("item_move_modifier")
    if any(
        hook in raw
        for hook in (
            "onAnyPseudoWeatherChange",
            "onPrimal",
            "onStart",
            "onSwitchIn",
            "onTerrainChange",
            "onUpdate",
        )
    ):
        if "onTerrainChange" in raw or name_key in terrain_seed_items:
            mechanics.add("item_terrain_seed")
        else:
            mechanics.add("item_start_trigger")
    if raw.get("isBerry") or "onEat" in raw or "onTryEatItem" in raw:
        mechanics.add("item_berry")
        if name_key in healing_berries:
            mechanics.add("item_berry_heal")
        if name_key in status_berries or "onAfterSetStatus" in raw:
            mechanics.add("item_status_cure")
        if name_key in stat_berries or raw.get("boosts"):
            mechanics.add("item_stat_berry")
    if "onTakeItem" in raw:
        mechanics.add("item_take_protection")
    if "onSetAbility" in raw:
        mechanics.add("item_ability_guard")
    if any(hook in raw for hook in ("onAfterBoost", "onTryBoost")):
        mechanics.add("item_boost_guard")
    if "onTrapPokemon" in raw:
        mechanics.add("item_escape")
    if "onFractionalPriority" in raw:
        mechanics.add("item_priority_modifier")
    if "onModifyEVs" in raw:
        mechanics.add("item_ev_modifier")
    if "onUse" in raw or name_key in bag_use_items:
        mechanics.add("item_bag_use")
    if raw.get("megaStone") or raw.get("megaEvolves") or raw.get("forcedForme") or raw.get("itemUser"):
        mechanics.add("item_form_metadata")
    if raw.get("onDrive") or raw.get("onMemory") or raw.get("onPlate"):
        mechanics.add("item_type_metadata")
    if raw.get("zMove") or raw.get("zMoveFrom") or raw.get("zMoveType"):
        mechanics.add("item_z_move_metadata")
    if raw.get("isPokeball"):
        mechanics.add("item_pokeball_metadata")
    if raw.get("naturalGift") and (not has_callback or raw.get("onEat") is False):
        mechanics.add("item_natural_gift_metadata")
    if raw.get("fling") and not has_callback:
        mechanics.add("item_fling_metadata")
    if name_key == "metalalloy":
        mechanics.add("item_no_battle_effect")
    if has_callback:
        mechanics.add("callback_behavior")
    return tuple(sorted(mechanics))


def infer_pokemon_mechanics(raw: Mapping[str, Any]) -> tuple[str, ...]:
    """Infer species/form mechanics that may require explicit contracts."""

    mechanics = set()
    name = str(raw.get("name") or "")
    name_key = normalize_key(name)
    forme = str(raw.get("forme") or "")
    is_mega_form = forme.startswith("Mega") or "mega" in normalize_key(forme) or "mega" in name_key
    ability_key = normalize_key(raw.get("requiredAbility"))
    has_form_metadata = bool(
        raw.get("battleOnly")
        or raw.get("forme")
        or raw.get("changesFrom")
        or raw.get("baseSpecies")
    )
    if not has_form_metadata:
        mechanics.add("species_identity")
    elif not (raw.get("requiredItem") or raw.get("requiredAbility") or raw.get("requiredMove")):
        mechanics.add("species_static_form_metadata")

    if raw.get("battleOnly") or "Gmax" in name or forme == "Gmax":
        mechanics.add("species_battle_only_form_metadata")
    if raw.get("requiredItem"):
        mechanics.add("species_item_requirement_metadata")
        if is_mega_form:
            mechanics.add("species_mega_evolution")
        else:
            if name_key in {"groudonprimal", "kyogreprimal"}:
                mechanics.add("species_primal_form_change")
            else:
                mechanics.add("species_item_form_change")
    if raw.get("requiredAbility"):
        mechanics.add("species_ability_form_metadata")
    if ability_key in {"forecast", "flowergift"}:
        mechanics.add("species_weather_form_change")
    if ability_key in {"schooling", "zenmode", "powerconstruct", "shieldsdown"}:
        mechanics.add("species_hp_form_change")
    if ability_key == "stancechange":
        mechanics.add("species_move_state_form_change")
    if ability_key == "zerotohero":
        mechanics.add("species_switch_form_change")
    if raw.get("requiredMove"):
        mechanics.add("species_move_requirement_metadata")
        if is_mega_form:
            mechanics.add("species_mega_evolution")
    return tuple(sorted(mechanics))


def classify_entry(kind: str, key: str, entry: Any) -> CoverageRecord:
    """Classify one dex entry against explicit and mechanic-group coverage."""

    name = entry_name(key, entry)
    subject = coverage_id(kind, name)
    contracts = CONTRACTS_BY_SUBJECT.get(subject, ())
    raw = entry_raw(entry)

    if kind == "move":
        mechanics = infer_move_mechanics(raw)
    elif kind == "ability":
        mechanics = infer_ability_mechanics(raw)
    elif kind == "item":
        mechanics = infer_item_mechanics(raw)
    else:
        mechanics = infer_pokemon_mechanics(raw)

    if subject in KNOWN_GAPS:
        return CoverageRecord(
            kind=kind,
            name=name,
            subject=subject,
            status=KNOWN_GAP,
            mechanics=mechanics,
            contracts=contracts,
            reason=KNOWN_GAPS[subject],
        )
    if contracts:
        return CoverageRecord(
            kind=kind,
            name=name,
            subject=subject,
            status=EXPLICIT_CONTRACT,
            mechanics=mechanics,
            contracts=contracts,
            reason="direct semantic outcome contract",
        )
    covered = sorted(set(mechanics) & SUPPORTED_MECHANICS)
    if covered:
        return CoverageRecord(
            kind=kind,
            name=name,
            subject=subject,
            status=MECHANIC_CONTRACT,
            mechanics=mechanics,
            reason=f"mechanic group covered: {', '.join(covered)}",
        )
    return CoverageRecord(
        kind=kind,
        name=name,
        subject=subject,
        status=SMOKE_ONLY,
        mechanics=mechanics,
        reason="covered only by dex smoke construction/execution tests",
    )


def build_inventory() -> tuple[CoverageRecord, ...]:
    """Return classification records for all loaded move, ability, item, and species entries."""

    from pokemon import dex

    groups = (
        ("move", getattr(dex, "MOVEDEX", {})),
        ("ability", getattr(dex, "ABILITYDEX", {})),
        ("item", getattr(dex, "ITEMDEX", {})),
        ("pokemon", getattr(dex, "POKEDEX", {})),
    )
    records = []
    for kind, entries in groups:
        for key, entry in entries.items():
            records.append(classify_entry(kind, str(key), entry))
    return tuple(records)


def inventory_summary(records: Iterable[CoverageRecord]) -> Counter[tuple[str, str]]:
    """Count inventory entries by kind and coverage status."""

    return Counter((record.kind, record.status) for record in records)


def format_inventory_report(records: Iterable[CoverageRecord]) -> str:
    """Render a compact text report for the mechanic coverage inventory."""

    records = tuple(records)
    summary = inventory_summary(records)
    lines = [
        "Battle outcome proof inventory",
        "",
        "Coverage status meanings:",
        f"- {EXPLICIT_CONTRACT}: exact dex entry is named by a semantic outcome contract.",
        f"- {MECHANIC_CONTRACT}: entry uses at least one mechanic group proven by the contract catalog.",
        f"- {SMOKE_ONLY}: entry is only covered by broad dex construction/execution smoke checks.",
        f"- {KNOWN_GAP}: entry is intentionally documented as unsupported or divergent.",
        "",
        "Supported mechanic groups:",
        ", ".join(sorted(SUPPORTED_MECHANICS)) or "(none)",
        "",
        "Summary:",
    ]
    for kind in ("move", "ability", "item", "pokemon"):
        total = sum(count for (record_kind, _status), count in summary.items() if record_kind == kind)
        parts = [f"{status}={summary[(kind, status)]}" for status in COVERAGE_STATUSES]
        lines.append(f"- {kind}: total={total}; " + ", ".join(parts))

    smoke_samples = [record for record in records if record.status == SMOKE_ONLY][:12]
    if smoke_samples:
        lines.extend(["", "Smoke-only examples:"])
        for record in smoke_samples:
            mechanic_text = ", ".join(record.mechanics) if record.mechanics else "no inferred battle mechanic"
            lines.append(f"- {record.kind}:{record.name} ({mechanic_text})")

    gap_records = [record for record in records if record.status == KNOWN_GAP]
    if gap_records:
        lines.extend(["", "Known gaps:"])
        for record in gap_records:
            lines.append(f"- {record.subject}: {record.reason}")

    return "\n".join(lines)


def main() -> None:
    print(format_inventory_report(build_inventory()))


if __name__ == "__main__":
    main()
