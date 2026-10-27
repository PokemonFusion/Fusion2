"""Historical-model-compatible marketplace inspection without automatic repair."""

from pokemon.services.placement_audit import PlacementProblem


def audit_market_v1(apps, using="default"):
    """Check actual listings; generic system claims retain their owning subsystem."""
    claims = apps.get_model("pokemon", "PokemonReservation").objects.using(using)
    placements = apps.get_model("pokemon", "PokemonPlacement").objects.using(using)
    pokemon = apps.get_model("pokemon", "OwnedPokemon").objects.using(using)
    for row in apps.get_model("pokemon", "MarketListing").objects.using(using).values():
        matching = claims.filter(kind="market", token=row["id"])
        valid = True
        if row["state"] == "active":
            valid = (row["pokemon_id"] == row["owned_id"] and row["seller_id"] == row["seller_character_id"]
                and matching.filter(pokemon_id=row["owned_id"], storage__user_id=row["seller_character_id"]).count() == 1
                and placements.filter(pokemon_id=row["owned_id"], storage__user_id=row["seller_character_id"],
                    location_type__in=("party", "box")).exists()
                and pokemon.filter(pk=row["owned_id"], trainer__user_id=row["seller_character_id"]).exists())
        elif matching.exists():
            valid = False
        if not valid:
            yield PlacementProblem(str(row["owned_id"]), "market_custody", f"listing={row['id']}")
