"""Historical-model-compatible audit of sealed breeding cycles and owned egg state."""

from pokemon.services.placement_audit import PlacementProblem


def valid_plan_v1(plan):
    """Keep v1's persisted trait shape stable for migration and recovery inspection."""
    if not isinstance(plan, dict) or plan.get("rule_version") != 1:
        return False
    if (not all(isinstance(plan.get(key), str) and plan[key] for key in ("species", "ability", "nature"))
            or plan.get("gender") not in {"M", "F", "N"} or type(plan.get("is_shiny")) is not bool):
        return False
    ivs, evs, moves = plan.get("ivs"), plan.get("evs"), plan.get("moves")
    return (isinstance(ivs, list) and len(ivs) == 6 and all(type(iv) is int and 0 <= iv <= 31 for iv in ivs)
        and isinstance(evs, list) and len(evs) == 6 and all(type(ev) is int and ev == 0 for ev in evs)
        and isinstance(moves, list) and 1 <= len(moves) <= 4
        and all(isinstance(move, str) and move for move in moves))


def audit_breeding_v1(apps, using="default"):
    """Report exact cycle/egg IDs without rerolling traits, payments or ownership."""
    cycles = apps.get_model("pokemon", "BreedingCycle").objects.using(using)
    eggs = apps.get_model("pokemon", "BreedingEgg").objects.using(using)
    entries = apps.get_model("pokemon", "DaycareEntry").objects.using(using)
    owned = apps.get_model("pokemon", "OwnedPokemon").objects.using(using)
    owners = dict(apps.get_model("pokemon", "UserStorage").objects.using(using).values_list("pk", "user_id"))
    for row in cycles.values():
        if row["storage_id"] is not None and owners.get(row["storage_id"]) != row["origin_character_id"]:
            yield PlacementProblem(str(row["egg_uuid"]), "breeding_origin", f"cycle={row['id']}")
        if not valid_plan_v1(row["plan"]):
            yield PlacementProblem(str(row["egg_uuid"]), "breeding_plan", f"cycle={row['id']}")
        linked = list(entries.filter(active_cycle_id=row["id"]).values())
        if row["state"] == "producing":
            by_id = {entry["id"]: entry for entry in linked}
            correct = (len(linked) == 2 and {entry["id"] for entry in linked} == {row["parent_a_id"], row["parent_b_id"]}
                and {entry["owned_id"] for entry in linked} == {row["parent_a_uuid"], row["parent_b_uuid"]}
                and by_id[row["parent_a_id"]]["owned_id"] == row["parent_a_uuid"]
                and by_id[row["parent_b_id"]]["owned_id"] == row["parent_b_uuid"]
                and all(entry["storage_id"] == row["storage_id"] and entry["state"] == "active" for entry in linked))
            if not correct:
                yield PlacementProblem(str(row["egg_uuid"]), "breeding_parent_links", f"cycle={row['id']}")
        elif linked:
            yield PlacementProblem(str(row["egg_uuid"]), "breeding_closed_parent_links", f"cycle={row['id']}")
        records = eggs.filter(cycle_id=row["id"])
        if (row["state"] == "collected" and not records.filter(pk=row["egg_uuid"]).exists()
                or row["state"] != "collected" and records.exists()):
            yield PlacementProblem(str(row["egg_uuid"]), "breeding_egg_count", f"cycle={row['id']}")
    for row in eggs.values():
        if row["pokemon_id"] is not None:
            source = owned.filter(pk=row["pokemon_id"]).values("is_egg").first()
            if (row["pokemon_id"] != row["id"] or source is None
                    or source["is_egg"] != (row["hatched_at"] is None)):
                yield PlacementProblem(str(row["id"]), "breeding_hatch_state", f"cycle={row['cycle_id']}")
