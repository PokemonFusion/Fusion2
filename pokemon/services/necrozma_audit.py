"""Versioned, read-only audit of native pairs and their canonical source resources."""

from collections import Counter

from pokemon.services.placement_audit import PlacementProblem


PAIRS = {
    "Necrozma-Dusk-Mane": ("Solgaleo", "Sunsteel Strike", "Full Metal Body"),
    "Necrozma-Dawn-Wings": ("Lunala", "Moongeist Beam", "Shadow Shield"),
}


def require_necrozma_baseline(apps, schema_editor):
    """Stop an ambiguous legacy upgrade before this feature's first schema write."""
    owned = apps.get_model("pokemon", "OwnedPokemon").objects.using(schema_editor.connection.alias)
    sources = {"sunsteelstrike", "moongeistbeam"}
    from pokemon.names import normalize_name

    invalid = [(pid, species) for pid, species in owned.values_list("pk", "species")
               if normalize_name(species) in {"necrozmaduskmane", "necrozmadawnwings"}][:20]
    base_ids = [pid for pid, species in owned.values_list("pk", "species") if normalize_name(species) == "necrozma"]
    moves = {row["id"] for row in apps.get_model("pokemon", "Move").objects.using(
        schema_editor.connection.alias).values() if normalize_name(row["name"]) in sources}
    for model, path in (("PokemonLearnedMove", "pokemon"), ("ActiveMoveslot", "pokemon"),
                        ("MovesetSlot", "moveset__pokemon")):
        invalid.extend(apps.get_model("pokemon", model).objects.using(schema_editor.connection.alias)
            .filter(**{path + "__pk__in": base_ids, "move_id__in": moves})
            .values_list(path + "_id" if path == "pokemon" else "moveset__pokemon_id", "move_id")[:20])
    if invalid:
        raise RuntimeError("Necrozma baseline audit failed; no automatic repairs: " + str(invalid[:20]))


def audit_necrozma_v1(apps, using="default"):
    """Identify ambiguous grants, role reuse, resources and bindings without repair.

    Keep this field contract stable: migration 0058 calls it with historical apps.
    Ordinary placement/mirror ownership is checked by the versioned parent audit.
    """
    def rows(model):
        return list(apps.get_model("pokemon", model).objects.using(using).values())

    owned = {row["unique_id"]: row for row in rows("OwnedPokemon")}
    placements = {row["pokemon_id"]: row for row in rows("PokemonPlacement")}
    storage = {row["id"]: row["user_id"] for row in rows("UserStorage")}
    trainers = {row["id"]: row["user_id"] for row in rows("Trainer")}
    pairs = rows("NecrozmaCombination")
    resources = {row["id"]: row for row in rows("NecrozmaResource")}
    moves = {row["id"]: row["name"] for row in rows("Move")}
    sets = {row["id"]: row for row in rows("Moveset")}
    active, slots, learned = rows("ActiveMoveslot"), rows("MovesetSlot"), rows("PokemonLearnedMove")
    boosts = {(row["pokemon_id"], row["move_id"]): row["bonus_pp"] for row in rows("MovePPBoost")}
    membership = Counter(pid for pair in pairs for pid in (pair["host_id"], pair["companion_id"]))
    hosts = {pair["host_id"]: pair for pair in pairs}
    companions = {pair["companion_id"]: pair for pair in pairs}
    for pid, count in membership.items():
        if count != 1:
            yield PlacementProblem(str(pid), "necrozma_role_reuse", f"memberships={count}")
    for pair in pairs:
        pid = pair["host_id"]
        host, companion = owned.get(pid), owned.get(pair["companion_id"])
        hp, cp = placements.get(pid), placements.get(pair["companion_id"])
        spec = PAIRS.get(pair["target_species"])
        if (not spec or not host or not companion or pair["base_species"] != "Necrozma"
                or pair["policy_version"] != 1 or pid == pair["companion_id"]
                or host["species"] != pair["target_species"] or companion["species"] != spec[0]
                or host["ability"] != "Prism Armor" or companion["ability"] != spec[2]
                or host["is_egg"] or companion["is_egg"]
                or host["trainer_id"] != companion["trainer_id"]
                or trainers.get(host["trainer_id"]) != storage.get(pair["storage_id"])
                or not hp or not cp or hp["storage_id"] != pair["storage_id"]
                or cp["storage_id"] != pair["storage_id"] or hp["location_type"] not in ("party", "box")
                or cp["location_type"] != "combined" or cp["combination_id"] != pair["id"]):
            yield PlacementProblem(str(pid), "necrozma_pair", f"pair={pair['id']}")
            continue
        resource = resources.get(pair["resource_id"])
        aset = sets.get(pair["moveset_id"])
        source_active = [row for row in active if row["pokemon_id"] == pid and row["slot"] == pair["move_slot"]]
        source_saved = [row for row in slots if row["moveset_id"] == pair["moveset_id"] and row["slot"] == pair["move_slot"]]
        if (not resource or resource["host_id"] != pid or resource["source"] != spec[1]
                or not aset or aset["pokemon_id"] != pid or host["active_moveset_id"] != aset["id"]
                or len(source_active) != 1 or len(source_saved) != 1
                or moves.get(source_active[0]["move_id"]) != spec[1]
                or source_saved[0]["move_id"] != source_active[0]["move_id"]
                or source_active[0]["current_pp"] != resource["current_pp"]
                or not any(row["pokemon_id"] == pid and row["move_id"] == source_active[0]["move_id"] for row in learned)):
            yield PlacementProblem(str(pid), "necrozma_binding", f"pair={pair['id']}")
    for pid, pokemon in owned.items():
        from pokemon.names import normalize_name

        if normalize_name(pokemon["species"]) in {"necrozmaduskmane", "necrozmadawnwings"} and pid not in hosts:
            yield PlacementProblem(str(pid), "necrozma_unpaired_form", pokemon["species"])
        placement = placements.get(pid)
        if placement and placement["location_type"] == "combined" and pid not in companions:
            yield PlacementProblem(str(pid), "necrozma_orphan_companion", "No active pair")
        # A source move is temporary native exposure only on a currently linked host.
        if normalize_name(pokemon["species"]) == "necrozma" or pid in hosts:
            exposures = [moves.get(row["move_id"]) for row in learned if row["pokemon_id"] == pid]
            exposures += [moves.get(row["move_id"]) for row in active if row["pokemon_id"] == pid]
            exposures += [moves.get(row["move_id"]) for row in slots
                          if sets.get(row["moveset_id"], {}).get("pokemon_id") == pid]
            permitted = PAIRS[hosts[pid]["target_species"]][1] if pid in hosts and hosts[pid]["target_species"] in PAIRS else None
            from pokemon.names import normalize_name

            unexpected = {name for name in exposures if normalize_name(name or "") in {
                "sunsteelstrike", "moongeistbeam"} and name != permitted}
            if unexpected:
                yield PlacementProblem(str(pid), "necrozma_unbound_source", str(sorted(unexpected)))
    for resource in resources.values():
        pid = resource["host_id"]
        pokemon = owned.get(pid)
        move_ids = [mid for mid, name in moves.items() if name == resource["source"]]
        bonus = boosts.get((pid, move_ids[0]), 0) if len(move_ids) == 1 else 0
        if (not pokemon or pokemon["species"] not in {"Necrozma", *PAIRS}
                or resource["source"] not in {spec[1] for spec in PAIRS.values()}
                or resource["policy_version"] != 1 or not 0 <= bonus <= 3
                or not 0 <= resource["current_pp"] <= 5 + bonus):
            yield PlacementProblem(str(pid), "necrozma_resource", f"resource={resource['id']}")
    from uuid import UUID

    history = set()
    for operation in rows("NecrozmaOperation"):
        terms = operation["terms"]
        if operation["action"] != "combine" or operation["state"] != "completed" or not isinstance(terms, dict):
            continue
        if terms.get("source") not in {spec[1] for spec in PAIRS.values()}:
            continue
        try:
            history.add((UUID(terms["host"]), terms["source"]))
        except (KeyError, ValueError, TypeError):
            yield PlacementProblem(str(operation["id"]), "necrozma_receipt", "Invalid retained host/source identity")
    present = {(row["host_id"], row["source"]) for row in resources.values()}
    for pid, source in history - present:
        if pid in owned:
            yield PlacementProblem(str(pid), "necrozma_missing_history_resource", source)
    for pid, source in present - history:
        yield PlacementProblem(str(pid), "necrozma_unintroduced_resource", source)
