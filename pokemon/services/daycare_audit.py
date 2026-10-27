"""Read-only, historical-model-compatible validation of canonical Daycare custody."""

from pokemon.services.placement_audit import PlacementProblem


def audit_daycare_v1(apps, using="default"):
    """Require one matching active entry and exclusive claim per deposited Pokemon."""
    entries = apps.get_model("pokemon", "DaycareEntry").objects.using(using)
    claims = apps.get_model("pokemon", "PokemonReservation").objects.using(using)
    placements = apps.get_model("pokemon", "PokemonPlacement").objects.using(using)
    active = {row["owned_id"]: row for row in entries.filter(state="active").values()}
    deposited = {row["pokemon_id"]: row for row in placements.filter(location_type="daycare").values()}
    for identifier in set(active) | set(deposited):
        entry, placement = active.get(identifier), deposited.get(identifier)
        if (not entry or not placement or entry["pokemon_id"] != identifier
                or entry["storage_id"] != placement["storage_id"]
                or not claims.filter(pokemon_id=identifier, storage_id=entry["storage_id"], kind="daycare", token=entry["id"]).exists()):
            yield PlacementProblem(str(identifier), "daycare_custody", f"entry={entry['id'] if entry else 'missing'}")
    for row in entries.exclude(state="active").values():
        if claims.filter(kind="daycare", token=row["id"]).exists():
            yield PlacementProblem(str(row["owned_id"]), "daycare_closed_claim", f"entry={row['id']}")
