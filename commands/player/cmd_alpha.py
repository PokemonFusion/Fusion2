"""Alpha-test convenience commands."""

from __future__ import annotations

from evennia import Command

from pokemon.data.starters import get_starter_names, resolve_starter_key
from utils.dex_suggestions import (
    is_species_not_found_error,
    normalize_dex_key,
    species_not_found_message,
    suggest_name,
)
from utils.locks import require_no_battle_lock

ALPHA_ROOM_FLAGS = (
    "alpha_test_area",
    "is_alpha_test_area",
    "alpha_testing",
)
ALPHA_GENERATED_FLAG = "alpha_test_generated"
ALPHA_MOVE_TERMINAL_FLAGS = (
    "alpha_move_terminal",
    "is_alpha_move_terminal",
)
ALPHA_MOVE_CATEGORIES = ("machine", "tutor")


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


def _is_alpha_move_terminal(obj) -> bool:
    """Return whether an object is an alpha move-learning terminal."""

    if any(_db_bool(obj, flag) for flag in ALPHA_MOVE_TERMINAL_FLAGS):
        return True
    key = str(getattr(obj, "key", "") or getattr(obj, "name", "") or "").lower()
    return key.startswith("alpha move terminal")


def _has_alpha_move_terminal(caller) -> bool:
    """Return whether caller is near an alpha move-learning terminal."""

    location = getattr(caller, "location", None)
    if location is None:
        return False
    return any(_is_alpha_move_terminal(obj) for obj in getattr(location, "contents", []) or [])


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


def _display_move_name(move_name: str) -> str:
    """Return a readable move name for a learnset key."""

    try:
        from pokemon.middleware import get_move_by_name

        _key, details = get_move_by_name(move_name)
    except Exception:
        details = None

    if isinstance(details, dict):
        display = details.get("name")
    else:
        display = getattr(details, "name", None)
        raw = getattr(details, "raw", None)
        if not display and isinstance(raw, dict):
            display = raw.get("name")
    if display:
        return str(display)
    return str(move_name).replace("_", " ").replace("-", " ").title()


def _alpha_teachable_moves(pokemon) -> dict[str, str]:
    """Return terminal-teachable machine/tutor moves keyed by normalized name."""

    species = getattr(pokemon, "species", getattr(pokemon, "name", "")) or ""
    try:
        from pokemon.middleware import get_moveset_by_name

        _name, moveset = get_moveset_by_name(species)
    except Exception:
        moveset = None
    if not moveset:
        return {}

    moves: dict[str, str] = {}
    for category in ALPHA_MOVE_CATEGORIES:
        for move in moveset.get(category, []) or []:
            display = _display_move_name(str(move))
            for key in {normalize_dex_key(move), normalize_dex_key(display)}:
                if key:
                    moves.setdefault(key, display)
    return moves


def _record_alpha_taught_move(pokemon, move_name: str) -> None:
    """Mark alpha-terminal moves so they can be audited or cleaned later."""

    flag = f"alpha_teach:{normalize_dex_key(move_name)}"
    flags = list(getattr(pokemon, "flags", []) or [])
    if flag in flags:
        return
    flags.append(flag)
    try:
        pokemon.flags = flags
    except Exception:
        return

    save = getattr(pokemon, "save", None)
    if not callable(save):
        return
    try:
        save(update_fields=["flags"])
    except TypeError:
        save()


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


class CmdAlphaLearnMove(Command):
    """Teach alpha-test machine or tutor moves from a nearby terminal.

    Usage:
      +alphalearn <slot>=<move>
      +alphalearn/list <slot>

    Notes:
      This only works in alpha testing rooms with an Alpha Move Terminal. It
      accepts machine and tutor moves from the Pokemon's existing learnset data.
    """

    key = "+alphalearn"
    aliases = ["+alpha/learn", "+alpha/teach", "+testlearn"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        if not _is_alpha_test_area(self.caller):
            self.caller.msg("You can only use this in the alpha testing area.")
            return
        if not _has_alpha_move_terminal(self.caller):
            self.caller.msg("You need to use this near an Alpha Move Terminal.")
            return

        switches = {switch.lower() for switch in getattr(self, "switches", [])}
        args = (self.args or "").strip()
        if "list" in switches:
            self._list_moves(args)
            return

        if "=" not in args:
            self.caller.msg("Usage: +alphalearn <slot>=<move> or +alphalearn/list <slot>")
            return
        left, right = [part.strip() for part in args.split("=", 1)]
        try:
            slot = int(left)
        except ValueError:
            self.caller.msg("Invalid slot number.")
            return
        move_name = right.strip()
        if not move_name:
            self.caller.msg("Usage: +alphalearn <slot>=<move>")
            return

        pokemon = self.caller.get_active_pokemon_by_slot(slot)
        if not pokemon:
            self.caller.msg("No Pokemon in that slot.")
            return

        teachable = _alpha_teachable_moves(pokemon)
        if not teachable:
            self.caller.msg(f"{pokemon.name} has no alpha terminal moves available.")
            return

        selected = teachable.get(normalize_dex_key(move_name))
        if not selected:
            message = f"{pokemon.name} cannot learn {move_name} through the alpha move terminal."
            suggestion = suggest_name(move_name, teachable.values())
            if suggestion:
                message += f" Did you mean {suggestion}?"
            self.caller.msg(message)
            return

        learned_moves = getattr(pokemon, "learned_moves", None)
        if learned_moves is not None and learned_moves.filter(name__iexact=selected).exists():
            self.caller.msg(f"{pokemon.name} already knows {selected}.")
            return

        from pokemon.utils.move_learning import learn_move

        learn_move(pokemon, selected, caller=self.caller, prompt=True)
        _record_alpha_taught_move(pokemon, selected)

    def _list_moves(self, args: str) -> None:
        try:
            slot = int(args.strip())
        except ValueError:
            self.caller.msg("Usage: +alphalearn/list <slot>")
            return

        pokemon = self.caller.get_active_pokemon_by_slot(slot)
        if not pokemon:
            self.caller.msg("No Pokemon in that slot.")
            return

        moves = sorted(set(_alpha_teachable_moves(pokemon).values()), key=str.lower)
        if not moves:
            self.caller.msg(f"{pokemon.name} has no alpha terminal moves available.")
            return
        self.caller.msg(f"Alpha terminal moves for {pokemon.name}:\n" + ", ".join(moves))
