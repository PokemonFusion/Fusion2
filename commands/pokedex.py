# mygame/commands/pokedex.py

from evennia import Command
from pokemon.middleware import (
    get_pokemon_by_number,
    get_pokemon_by_name,
    format_pokemon_details,
    get_move_by_name,
    format_move_details,
    get_moveset_by_name,
    format_moveset,
)
from pokemon.dex.functions.pokedex_funcs import (
    get_region_entries,
    get_national_entries,
)

class CmdPokedexSearch(Command):
    """Look up Pokédex entries and lists.

    Usage:
      pokedex <name or number>
      +dex[/<region>] [<name or number>]
      poke <name or number>

    Calling ``+dex`` or ``+dex/<region>`` with no argument will list all Pokémon
    in the national or regional dex. When a number is given it is interpreted as
    the entry number for that dex.

    Regions: Alola, Galar, Hoenn, Johto, Kalos, Kanto, Sinnoh, Unova
    """

    key = "pokedex"
    aliases = ["+dex", "poke"]  # Adding aliases
    locks = "cmd:all()"
    help_category = "Pokemon/Dex"

    def parse(self):
        """Parse optional /region switch."""
        args = self.args.strip()
        self.switches = []
        if args.startswith("/"):
            parts = args[1:].split(None, 1)
            self.switches = parts[0].split("/")
            args = parts[1] if len(parts) > 1 else ""
        self.args = args.strip()

    def _list_entries(self, entries, include_forms=False):
        lines = []
        for num, key in entries:
            if num <= 0:
                continue
            canonical, details = get_pokemon_by_name(key)
            display_name = None
            if isinstance(details, dict):
                display_name = details.get("name")
            else:
                display_name = getattr(details, "name", None)
            if display_name is None:
                display_name = canonical

            forme = None
            if isinstance(details, dict):
                forme = details.get("forme")
            else:
                forme = getattr(details, "forme", None)

            if not include_forms:
                if forme and ("mega" in forme.lower() or "gmax" in forme.lower()):
                    continue
                if "mega" in key.lower() or "gmax" in key.lower():
                    continue
                if "mega" in display_name.lower() or "gmax" in display_name.lower():
                    continue

            symbol = ""
            if hasattr(self.caller, "get_dex_symbol"):
                symbol = self.caller.get_dex_symbol(canonical)
            lines.append(f"{num:>3}. {display_name} ({canonical}) {symbol}")
        self.caller.msg("\n".join(lines))

    def func(self):
        args = self.args.strip()
        region = self.switches[0].lower() if self.switches else None

        if not args:
            if region:
                try:
                    entries = get_region_entries(region)
                except KeyError:
                    self.caller.msg("Unknown region.")
                    return
            else:
                entries = get_national_entries()
            self._list_entries(entries)
            return

        if region:
            try:
                entries = get_region_entries(region)
            except KeyError:
                self.caller.msg("Unknown region.")
                return
            if args.isdigit():
                rnum = int(args)
                species = next((n for num, n in entries if num == rnum), None)
                if not species:
                    self.caller.msg("No Pokémon with that number in this region.")
                    return
                name, details = get_pokemon_by_name(species)
            else:
                name, details = get_pokemon_by_name(args)
        else:
            if args.isdigit():
                num = int(args)
                name, details = get_pokemon_by_number(num)
            else:
                name, details = get_pokemon_by_name(args)

        if name and details:
            self.caller.msg(format_pokemon_details(name, details))
        else:
            self.caller.msg("No Pokémon found with that name or number.")


class CmdPokedexAll(CmdPokedexSearch):
    """List all positive-numbered Pokémon.

    Usage:
      +dex/all
    """

    key = "+dex/all"
    aliases = ["pokedex/all"]
    locks = "cmd:all()"
    help_category = "Pokemon/Dex"

    def func(self):
        entries = get_national_entries()
        self._list_entries(entries, include_forms=True)


class CmdMovedexSearch(Command):
    """Search the movedex by move name.

    Usage:
      movedex <name>
    """

    key = "movedex"
    aliases = ["mdex", "move"]
    locks = "cmd:all()"
    help_category = "Pokemon/Dex"

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
    """Show the moveset for a Pokémon.

    Usage:
      moveset <pokemon>
    """

    key = "moveset"
    aliases = ["learnset", "movelist"]
    locks = "cmd:all()"
    help_category = "Pokemon/Dex"

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


class CmdPokedexNumber(Command):
    """Lookup a Pokémon by its National Dex number.

    Usage:
      pokenum <number>
    """

    key = "pokenum"
    aliases = ["dexnum"]
    locks = "cmd:all()"
    help_category = "Pokemon/Dex"

    def func(self):
        arg = self.args.strip()
        if not arg.isdigit():
            self.caller.msg("Usage: pokenum <number>")
            return
        num = int(arg)
        name, details = get_pokemon_by_number(num)
        if not name:
            self.caller.msg("No Pokémon found with that number.")
            return
        self.caller.msg(format_pokemon_details(name, details))


from pokemon.starters import get_starter_names


class CmdStarterList(Command):
    """List valid starter Pokémon.

    Usage:
      starterlist
    """

    key = "starterlist"
    aliases = ["starters"]
    locks = "cmd:all()"
    help_category = "Pokemon/Dex"

    def func(self):
        names = get_starter_names()
        self.caller.msg("Starter Pokémon:\n" + ", ".join(names))

