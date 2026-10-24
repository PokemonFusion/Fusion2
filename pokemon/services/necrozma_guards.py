"""Shared native-pair eligibility without reversing an owning writer's locks.

Callers serialize mutations with character/storage/owned locks in their existing
order. These checks never acquire a character lock from a storage-first writer.
"""

from pokemon.names import normalize_name
from pokemon.services.placement import PlacementError


class NecrozmaError(PlacementError):
    """A native pair request cannot safely change either retained source."""


FUSED_KEYS = {"necrozmaduskmane", "necrozmadawnwings"}
HOST_OPERATIONS = frozenset({"field", "held", "pp", "heal", "progression", "battle", "inspect"})


def assert_human(character):
    """Keep native combination and initial battle support in current human form."""
    from pokemon.services.battle_rewards import BattleRewards

    if (BattleRewards.stored_attribute(character, "fusion_id")
            or BattleRewards.stored_attribute(character, "fusion_kind") is not None
            or normalize_name(BattleRewards.stored_attribute(character, "morphology") or "Human") != "human"):
        raise NecrozmaError("Return to human form before using a native Necrozma pair in battle or combining/separating it.")


def assert_owned_creation(species):
    """A direct fused grant/capture can never stand in for two real owned sources."""
    if normalize_name(species) in FUSED_KEYS:
        raise NecrozmaError("Acquire base Necrozma and Solgaleo or Lunala, then combine them at a Pokemon Center.")


def current_pair(pokemon_id):
    """Resolve either role from SQL; validate provenance even for read-only use."""
    from pokemon.models.core import OwnedPokemon
    from pokemon.models.necrozma import NecrozmaCombination
    from django.db.models import Q

    pairs = list(NecrozmaCombination.objects.filter(Q(host_id=pokemon_id) | Q(companion_id=pokemon_id)).values())
    if not pairs:
        species = OwnedPokemon.objects.filter(pk=pokemon_id).values_list("species", flat=True).first()
        if normalize_name(species or "") in FUSED_KEYS:
            raise NecrozmaError("This fused Necrozma has no valid live pair; ask staff to inspect it.")
        return None
    if len(pairs) != 1:
        raise NecrozmaError("Conflicting native pair roles require staff review.")
    pair = pairs[0]
    validate_pair(pair)
    return pair


def validate_pair(pair):
    """Require both actual owned sources, reciprocal custody and the bound source."""
    from pokemon.models.core import OwnedPokemon
    from pokemon.models.moves import ActiveMoveslot, MovesetSlot, PokemonLearnedMove
    from pokemon.models.necrozma import NecrozmaResource
    from pokemon.models.ownership import PokemonReservation
    from pokemon.models.storage import PokemonPlacement, UserStorage
    from pokemon.models.storage import ActivePokemonSlot, StorageBox
    from pokemon.services.necrozma_audit import PAIRS
    from pokemon.services.ownership import fusion_references

    rows = {row["unique_id"]: row for row in OwnedPokemon.objects.filter(
        pk__in=(pair["host_id"], pair["companion_id"])).values()}
    host, companion = rows.get(pair["host_id"]), rows.get(pair["companion_id"])
    spec = PAIRS.get(pair["target_species"])
    storage = UserStorage.objects.filter(pk=pair["storage_id"]).first()
    placements = {row["pokemon_id"]: row for row in PokemonPlacement.objects.filter(
        pokemon_id__in=rows).values()}
    hp, cp = placements.get(pair["host_id"]), placements.get(pair["companion_id"])
    if (not spec or not host or not companion or not storage or pair["host_id"] == pair["companion_id"]
            or pair["base_species"] != "Necrozma" or pair["policy_version"] != 1
            or host["species"] != pair["target_species"] or host["ability"] != "Prism Armor"
            or companion["species"] != spec[0] or companion["ability"] != spec[2]
            or host["trainer_id"] != companion["trainer_id"] or host["is_egg"] or companion["is_egg"]
            or not OwnedPokemon.objects.filter(pk=pair["host_id"], trainer__user_id=storage.user_id).exists()
            or not hp or not cp or hp["storage_id"] != storage.pk or cp["storage_id"] != storage.pk
            or hp["location_type"] not in {"party", "box"} or cp["location_type"] != "combined"
            or cp["combination_id"] != pair["id"]
            or PokemonReservation.objects.filter(pokemon_id__in=rows).exists()
            or {str(pid) for pid in rows} & fusion_references(storage.user)):
        raise NecrozmaError("The native pair's ownership or reservation is inconsistent; ask staff to inspect it.")
    for identifier, placement in ((pair["host_id"], hp), (pair["companion_id"], cp)):
        active = set(ActivePokemonSlot.objects.filter(pokemon_id=identifier).values_list("storage_id", "slot"))
        stored = set(UserStorage.stored_pokemon.through.objects.filter(ownedpokemon_id=identifier).values_list("userstorage_id", flat=True))
        boxed = set(StorageBox.pokemon.through.objects.filter(ownedpokemon_id=identifier).values_list("storagebox_id", flat=True))
        expected = (set(), set(), set())
        if placement["location_type"] == "party":
            expected = ({(storage.pk, placement["slot"])}, set(), set())
        elif placement["location_type"] == "box":
            expected = (set(), {storage.pk}, {placement["box_id"]})
        if (active, stored, boxed) != expected:
            raise NecrozmaError("The native pair's canonical placement and legacy mirrors conflict; ask staff to inspect it.")
    resource = NecrozmaResource.objects.filter(pk=pair["resource_id"], host_id=pair["host_id"],
        source=spec[1], policy_version=1).values().first()
    active = ActiveMoveslot.objects.filter(pokemon_id=pair["host_id"], slot=pair["move_slot"]).values(
        "move_id", "move__name", "current_pp").first()
    if (not resource or not active or active["move__name"] != spec[1]
            or active["current_pp"] != resource["current_pp"]
            or host["active_moveset_id"] != pair["moveset_id"]
            or not MovesetSlot.objects.filter(moveset_id=pair["moveset_id"], moveset__pokemon_id=pair["host_id"],
                slot=pair["move_slot"], move_id=active["move_id"]).exists()
            or not PokemonLearnedMove.objects.filter(pokemon_id=pair["host_id"], move_id=active["move_id"]).exists()):
        raise NecrozmaError("The native source move/PP binding needs staff review; nothing was changed.")


def assert_operation(pokemon_id, operation="placement"):
    """Freeze every companion writer and allow only reviewed host operations."""
    pair = current_pair(pokemon_id)
    if pair is None:
        return None
    if str(pair["companion_id"]) == str(pokemon_id):
        if operation == "inspect":
            return pair
        raise NecrozmaError("This Pokemon is reserved as Necrozma's companion. Separate the pair first.")
    if operation not in HOST_OPERATIONS:
        raise NecrozmaError("Separate this native Necrozma pair before changing placement, ability, species, movesets or ownership.")
    if operation == "battle":
        from pokemon.models.storage import UserStorage

        assert_human(UserStorage.objects.get(pk=pair["storage_id"]).user)
    return pair
