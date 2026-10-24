"""Live native-pair provenance for ordinary owned battles and two existing Z routes."""

from pokemon.names import normalize_name


class NativeNecrozmaBattle:
    """A persistent native pair grants provenance, never a battle mechanic budget."""

    @staticmethod
    def proof(pair):
        """Keep lifecycle identity stable while health, PP and progression change."""
        return {"lifecycle": str(pair["id"]), "version": pair["policy_version"],
                "host": str(pair["host_id"]), "companion": str(pair["companion_id"]),
                "species": pair["target_species"], "moveset": pair["moveset_id"],
                "slot": pair["move_slot"], "resource": pair["resource_id"]}

    @staticmethod
    def matches(recorded, expected):
        """Reject extra keys and bool/float substitutions for issued integer fields."""
        from collections.abc import Mapping

        return (isinstance(recorded, Mapping) and set(recorded) == set(expected)
            and all(type(recorded[key]) is type(value) and recorded[key] == value for key, value in expected.items()))

    @classmethod
    def bind(cls, model, pokemon):
        """Build only from a current valid host; a companion never enters a roster."""
        from pokemon.services.necrozma_moves import pair_for_model

        pair = pair_for_model(model, "battle")
        if pair:
            pokemon.native_origin = dict(pokemon.native_origin or {}, necrozma=cls.proof(pair))

    @classmethod
    def validate_actor(cls, battle, participant, pokemon, *, row=None):
        """Require current authority and exact pair proof at every mutation boundary."""
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.pokemon_refs import parse_pokemon_ref
        from pokemon.battle.owned_battle_actor import BattleOwnershipChanged

        origin = getattr(pokemon, "native_origin", None) or {}
        recorded = origin.get("necrozma")
        player = getattr(participant, "player", None)
        if not BattleRewards.supports(player) or getattr(participant, "is_ai", True):
            if recorded:
                raise BattleOwnershipChanged("A native Necrozma pair requires its ordinary human controller.")
            return None
        kind, identifier = parse_pokemon_ref(getattr(pokemon, "model_id", None))
        if kind != "owned" or not identifier:
            if recorded:
                raise BattleOwnershipChanged("Native pair provenance cannot be copied onto an encounter.")
            return None
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.necrozma_guards import assert_operation

        try:
            pair = assert_operation(identifier, "battle")
        except ValueError as error:
            raise BattleOwnershipChanged(str(error)) from error
        if pair is None:
            if recorded:
                raise BattleOwnershipChanged("That native combination lifecycle is no longer active.")
            return None
        character = BattleRewards.character(player)
        if (not cls.matches(recorded, cls.proof(pair)) or origin.get("ref") != str(pokemon.model_id)
                or origin.get("species") != pair["target_species"]
                or not OwnedPokemon.objects.filter(pk=identifier, trainer__user_id=character.pk).exists()
                or len(battle.participants) != 2 or getattr(battle, "multi", False)
                or getattr(battle.type, "name", "") not in {"WILD", "TRAINER", "PVP"}
                or any(getattr(part, "max_active", 1) not in {1, 2} for part in battle.participants)
                or getattr(pokemon, "mega_evolved", False) or getattr(pokemon, "terastallized", None)
                or "dynamax" in (getattr(pokemon, "volatiles", None) or {})):
            raise BattleOwnershipChanged("Native Necrozma provenance, controller or supported battle format changed; recovery is required.")
        return pair

    @classmethod
    def validate_roster(cls, battle):
        """Check every owned member, including reserves and a forged companion row."""
        for participant in getattr(battle, "participants", []):
            for pokemon in participant.pokemons:
                cls.validate_actor(battle, participant, pokemon)

    @staticmethod
    def lock_sources(battle):
        """Hold native owners/storage/trainer/sources before any turn or sync writes."""
        from django.db import connection
        from pokemon.services.battle_rewards import BattleRewards

        owners = sorted({BattleRewards.character(part.player).pk for part in battle.participants
            if BattleRewards.supports(getattr(part, "player", None)) and any(
                (getattr(mon, "native_origin", None) or {}).get("necrozma") for mon in part.pokemons)})
        if not owners:
            return
        if not connection.in_atomic_block:
            raise ValueError("Native battle source locks require an enclosing transaction.")
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.ownership import locked_owners

        with locked_owners(owners):
            list(OwnedPokemon.objects.select_for_update().filter(trainer__user_id__in=owners).order_by("pk").values("pk"))

    @classmethod
    def signature_allowed(cls, profile, pokemon, row):
        """Add exactly two live-pair exceptions without changing native Z profiles."""
        origin = getattr(pokemon, "native_origin", None) or {}
        if not origin.get("necrozma"):
            return False
        from pokemon.services.pokemon_refs import parse_pokemon_ref
        from pokemon.services.necrozma_guards import assert_operation

        kind, identifier = parse_pokemon_ref(getattr(pokemon, "model_id", None))
        if kind != "owned":
            return False
        pair = assert_operation(identifier, "battle")
        return bool(pair and cls.matches(origin["necrozma"], cls.proof(pair))
            and row["species"] == pair["target_species"]
            and str(pokemon.species) == row["species"] and not getattr(pokemon, "transformed", False)
            and (row["species"], normalize_name(profile.crystal), normalize_name(profile.source)) in {
                ("Necrozma-Dusk-Mane", "solganiumz", "sunsteelstrike"),
                ("Necrozma-Dawn-Wings", "lunaliumz", "moongeistbeam"),
            })
