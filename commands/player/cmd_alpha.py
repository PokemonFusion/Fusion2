"""Alpha-test convenience commands."""

from __future__ import annotations

from evennia import Command

from pokemon.data.starters import get_starter_names, resolve_starter_key
from utils.dex_suggestions import is_species_not_found_error, species_not_found_message
from utils.locks import require_no_battle_lock

ALPHA_ROOM_FLAGS = (
    "alpha_test_area",
    "is_alpha_test_area",
    "alpha_testing",
)
ALPHA_GENERATED_FLAG = "alpha_test_generated"


def _db_bool(obj, attr: str, default: bool = False) -> bool:
    db = getattr(obj, "db", None)
    if db is None:
        return default
    try:
        return bool(getattr(db, attr))
    except Exception:
        return default


def _is_alpha_test_area(caller) -> bool:
    """Return whether caller is standing in an alpha testing room."""

    location = getattr(caller, "location", None)
    if location is None:
        return False
    if any(_db_bool(location, flag) for flag in ALPHA_ROOM_FLAGS):
        return True
    key = str(getattr(location, "key", "") or getattr(location, "name", "") or "").lower()
    return key.startswith("alpha ")


def _placement_message(pokemon, placement: str, box_name: str | None = None) -> str:
    display = getattr(pokemon, "name", None) or getattr(pokemon, "species", "Pokemon")
    level = getattr(pokemon, "computed_level", getattr(pokemon, "level", 5))
    if placement == "party":
        slot = getattr(pokemon, "party_slot", None)
        suffix = f" in party slot {slot}" if slot else " in your party"
        return f"Added {display} (Lv {level}){suffix}."
    return f"Added {display} (Lv {level}) to {box_name or 'storage'} because your party is full."


def _alpha_met_location(location_name: str) -> str:
    if location_name:
        return f"Alpha Test Generator ({location_name})"
    return "Alpha Test Generator"


class CmdAlphaPokemon(Command):
    """Add a chargen-valid Pokemon for alpha testing.

    Usage:
      +alphapokemon <species>
      +alphapokemon/list

    Notes:
      This only works in alpha testing rooms. Species must be valid on the
      chargen starter list.
    """

    key = "+alphapokemon"
    aliases = ["+alpha/pokemon", "+testpokemon"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        if not _is_alpha_test_area(self.caller):
            self.caller.msg("You can only use this in the alpha testing area.")
            return

        switches = {switch.lower() for switch in getattr(self, "switches", [])}
        species_arg = (self.args or "").strip()
        if "list" in switches or species_arg.lower() in {"list", "starterlist", "starters"}:
            self.caller.msg("Alpha Pokemon choices:\n" + ", ".join(get_starter_names()))
            return
        if not species_arg:
            self.caller.msg("Usage: +alphapokemon <species> or +alphapokemon/list")
            return

        species_key = resolve_starter_key(species_arg)
        if not species_key:
            self.caller.msg("That Pokemon is not valid on the chargen starter list. Use +starters to check options.")
            return

        trainer = getattr(self.caller, "trainer", None)
        storage = getattr(self.caller, "storage", None)
        if trainer is None or storage is None:
            self.caller.msg("You need a trainer record and Pokemon storage first.")
            return

        try:
            pokemon, placement, box_name = self._create_and_place(species_key, trainer, storage)
        except ValueError as err:
            if is_species_not_found_error(err):
                self.caller.msg(species_not_found_message(species_arg))
            else:
                self.caller.msg(str(err))
            return

        self.caller.msg(_placement_message(pokemon, placement, box_name))

    def _create_and_place(self, species_key: str, trainer, storage):
        """Generate a level-5 Pokemon and place it like capture overflow."""

        from django.db import transaction
        from django.utils import timezone

        from pokemon.data.generation import generate_pokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.storage import assign_to_first_storage_box, move_to_box, move_to_party

        instance = generate_pokemon(species_key, level=5)
        location = getattr(self.caller, "location", None)
        location_name = str(getattr(location, "key", "") or getattr(location, "name", "") or "")
        user = getattr(trainer, "user", None)

        with transaction.atomic():
            pokemon = create_owned_pokemon(
                instance.species.name,
                trainer,
                instance.level,
                gender=getattr(instance, "gender", "N"),
                nature=getattr(instance, "nature", ""),
                ability=getattr(instance, "ability", ""),
                ivs=[
                    getattr(getattr(instance, "ivs", None), "hp", 0),
                    getattr(getattr(instance, "ivs", None), "attack", 0),
                    getattr(getattr(instance, "ivs", None), "defense", 0),
                    getattr(getattr(instance, "ivs", None), "special_attack", 0),
                    getattr(getattr(instance, "ivs", None), "special_defense", 0),
                    getattr(getattr(instance, "ivs", None), "speed", 0),
                ],
                evs=[0, 0, 0, 0, 0, 0],
                met_level=instance.level,
                met_location=_alpha_met_location(location_name),
                met_date=timezone.now(),
                obtained_method="alpha_test",
                original_trainer=trainer,
                original_trainer_name=str(getattr(user, "key", "") or getattr(user, "name", "")),
                flags=[ALPHA_GENERATED_FLAG],
                active_move_names=list(getattr(instance, "moves", []) or []),
            )

            party = storage.get_party() if hasattr(storage, "get_party") else []
            if len(list(party or [])) < 6:
                move_to_party(pokemon, storage)
                placement = "party"
                box_name = None
            else:
                box = assign_to_first_storage_box(storage, pokemon)
                box = move_to_box(pokemon, storage, box)
                placement = "storage"
                box_name = getattr(box, "name", None)

        log_caught = getattr(trainer, "log_caught_pokemon", None)
        if callable(log_caught):
            try:
                log_caught(getattr(pokemon, "species", species_key))
            except Exception:
                pass
        return pokemon, placement, box_name
