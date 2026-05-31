# mygame/commands/cmd_pokedex.py

from evennia import Command

from pokemon.dex.functions.pokedex_funcs import (
    get_national_entries,
    get_region_entries,
)
from pokemon.middleware import (
    POKEMON_BY_NAME,
    _normalize_key,
    format_item_details,
    format_move_details,
    format_moveset,
    format_pokemon_details,
    get_item_by_name,
    get_move_by_name,
    get_moveset_by_name,
    get_pokemon_by_name,
    get_pokemon_by_number,
)
from utils.dex_suggestions import (
    item_not_found_message,
    learnset_not_found_message,
    move_not_found_message,
    pokemon_not_found_message,
)


class CmdPokedexSearch(Command):
    """Look up Pokedex entries and lists.

    Usage:
      +dex [<name or number>]
      +dex[/<region>] [<name or number>]

    Examples:
      +dex
      +dex Pikachu
      +dex/kanto 25

    Notes:
      Calling +dex or +dex/<region> with no argument will list all Pokemon
    in the national or regional dex. When a number is given it is interpreted as
    the entry number for that dex.

    Regions: Alola, Galar, Hoenn, Johto, Kalos, Kanto, Sinnoh, Unova
    """

    key = "+dex"
    aliases = ["pokedex", "poke"]
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
        for entry in entries:
            if len(entry) == 3:
                num, canonical, details = entry
            else:
                num, key = entry
                canonical, details = POKEMON_BY_NAME.get(_normalize_key(key), (key, None))
            if num <= 0:
                continue

            if details:
                if isinstance(details, dict):
                    display_name = details.get("name", canonical)
                    forme = details.get("forme")
                else:
                    display_name = getattr(details, "name", canonical)
                    forme = getattr(details, "forme", None)
            else:
                display_name = canonical
                forme = None

            if not include_forms:
                if forme and ("mega" in forme.lower() or "gmax" in forme.lower()):
                    continue
                if "mega" in canonical.lower() or "gmax" in canonical.lower():
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
            self.caller.msg(pokemon_not_found_message(args, "No Pokémon found with that name or number."))


class CmdPokedexAll(CmdPokedexSearch):
    """List all positive-numbered Pokemon.

    Usage:
      +dex/all

    Examples:
      +dex/all

    Notes:
      This includes alternate forms that the normal dex list hides.
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
      +movedex <name>

    Examples:
      +movedex Thunderbolt

    Notes:
      Use +teach when you want to teach a move to one of your Pokemon.
    """

    key = "+movedex"
    aliases = ["movedex", "+mdex", "mdex", "move"]
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
            self.caller.msg(move_not_found_message(args, "No move found with that name."))


class CmdItemdexSearch(Command):
    """Look up item information.

    Usage:
      +itemdex <item>

    Examples:
      +itemdex Potion

    Notes:
      +item is reserved for battle item use, so item lookup stays on +itemdex.
    """

    key = "+itemdex"
    aliases = ["itemdex"]
    locks = "cmd:all()"
    help_category = "Pokemon/Dex"

    def func(self):
        args = self.args.strip()

        if not args:
            self.caller.msg("You need to specify an item name to search for.")
            return

        name, details = get_item_by_name(args)

        if name and details:
            self.caller.msg(format_item_details(name, details))
        else:
            self.caller.msg(item_not_found_message(args, "No item found with that name."))


class CmdMovesetSearch(Command):
    """Show a Pokemon's learnset.

    Usage:
      +learnset <pokemon>

    Examples:
      +learnset Pikachu

    Notes:
      This is reference data. Use +learn or +teach to change one of your Pokemon.
    """

    key = "+learnset"
    aliases = ["moveset", "learnset", "movelist"]
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
            self.caller.msg(learnset_not_found_message(args, "No moveset found for that Pokémon."))


class CmdPokedexNumber(Command):
    """Look up a Pokemon by its National Dex number.

    Usage:
      +dexnum <number>

    Examples:
      +dexnum 25

    Notes:
      +dex <number> also looks up National Dex numbers.
    """

    key = "+dexnum"
    aliases = ["pokenum", "dexnum"]
    locks = "cmd:all()"
    help_category = "Pokemon/Dex"

    def func(self):
        arg = self.args.strip()
        if not arg.isdigit():
            self.caller.msg("Usage: +dexnum <number>")
            return
        num = int(arg)
        name, details = get_pokemon_by_number(num)
        if not name:
            self.caller.msg("No Pokémon found with that number.")
            return
        self.caller.msg(format_pokemon_details(name, details))


from pokemon.data.starters import get_starter_names


class CmdStarterList(Command):
    """List valid starter Pokemon.

    Usage:
      +starters

    Examples:
      +starters

    Notes:
      Starter selection happens inside chargen. Use +starter with no arguments
      only to open or resume that chargen menu path.
    """

    key = "+starters"
    aliases = ["starterlist", "starters"]
    locks = "cmd:all()"
    help_category = "Pokemon/Dex"

    def func(self):
        names = get_starter_names()
        self.caller.msg("Starter Pokémon:\n" + ", ".join(names))
