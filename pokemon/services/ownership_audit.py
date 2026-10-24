"""Versioned, historical-model-compatible ownership/reservation audit."""

from pokemon.services.placement_audit import PlacementProblem, audit_placements_v1


def audit_ownership_v1(apps, using="default"):
    """Report exact identifiers; never infer consent or repair stranded assets."""
    yield from audit_placements_v1(apps, using)
    reservations = apps.get_model("pokemon", "PokemonReservation")
    transfers = apps.get_model("pokemon", "OwnershipTransfer")
    placements = apps.get_model("pokemon", "PokemonPlacement")
    rows = {row["pokemon_id"]: row for row in placements.objects.using(using).values()}
    operations = {row["id"]: row for row in transfers.objects.using(using).values()}
    owners = dict(apps.get_model("pokemon", "UserStorage").objects.using(using).values_list("pk", "user_id"))
    for row in reservations.objects.using(using).values():
        pokemon_id = row["pokemon_id"]
        placement = rows.get(pokemon_id)
        if (not placement or placement["storage_id"] != row["storage_id"]
                or placement["location_type"] not in ("party", "box")):
            yield PlacementProblem(str(pokemon_id), "reservation_placement", f"reservation={row['id']}")
        operation = operations.get(row["transfer_id"])
        owner_id = owners.get(row["storage_id"])
        if row["kind"] == "trade" and (
            not operation or operation["state"] != "pending" or operation["id"] != row["token"]
            or owner_id not in operation["approvals"] or not any(
                move.get("pokemon") == str(pokemon_id) and move.get("source") == owner_id
                for move in operation["terms"])
        ):
            yield PlacementProblem(str(pokemon_id), "reservation_consent", f"transfer={row['transfer_id']}")


def audit_ownership_v2(apps, using="default"):
    """Extend v1 for Daycare without changing historical migration validation."""
    from pokemon.services.placement_audit import audit_placements_v2
    from pokemon.services.market_audit import audit_market_v1

    yield from audit_placements_v2(apps, using)
    yield from audit_market_v1(apps, using)
    valid_daycare = {str(row["pokemon_id"]) for row in apps.get_model("pokemon", "PokemonReservation").objects.using(using)
        .filter(kind="daycare", pokemon__placement__location_type="daycare").values()}
    for problem in audit_ownership_v1(apps, using):
        if problem.code in {"reservation_placement", "reservation_consent"}:
            if problem.code == "reservation_placement" and problem.pokemon_id in valid_daycare:
                continue
            yield problem
