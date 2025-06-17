# mygame/commands/pokedex.py

from evennia import Command
from fusion2.pokemon.middleware import (
    get_pokemon_by_number,
    get_pokemon_by_name,
    format_pokemon_details,
    get_move_by_name,
    format_move_details,
    get_moveset_by_name,
    format_moveset,
)

class CmdPokedexSearch(Command):
    """
    Search the Pokedex by name or number.

    Usage:
      pokedex <name or number>
      +dex <name or number>
      poke <name or number>

    Examples:
      pokedex Bulbasaur
      pokedex 1
      +dex Bulbasaur
      poke 1

    """
    key = "pokedex"
    aliases = ["+dex", "poke"]  # Adding aliases
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        args = self.args.strip()

        if not args:
            self.caller.msg("You need to specify a name or number to search for.")
            return

        if args.isdigit():
            # Search by number
            pokemon_id = int(args)
            name, details = get_pokemon_by_number(pokemon_id)
        else:
            # Search by name
            name, details = get_pokemon_by_name(args)

        if name and details:
            self.caller.msg(format_pokemon_details(name, details))
        else:
            self.caller.msg("No Pokémon found with that name or number.")


class CmdMovedexSearch(Command):
    """Search the movedex by move name."""

    key = "movedex"
    aliases = ["mdex", "move"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        args = self.args.strip()

        if not args:
            self.caller.msg("You need to specify a move name to search for.")
            return

        name, details = get_move_by_name(args)

        if name and details:
            self.caller.msg(format_move_details(name, details))
        else:
            self.caller.msg("No move found with that name.")


class CmdMovesetSearch(Command):
    """Show the moveset for a Pokémon."""

    key = "moveset"
    aliases = ["learnset", "movelist"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        args = self.args.strip()
        if not args:
            self.caller.msg("You need to specify a Pokémon name.")
            return

        name, moveset = get_moveset_by_name(args)
        if name and moveset:
            self.caller.msg(format_moveset(name, moveset))
        else:
            self.caller.msg("No moveset found for that Pokémon.")
