from evennia import Command
from django.db.utils import OperationalError
from utils.sheet_display import display_pokemon_sheet

class CmdSheet(Command):
    """Display details about Pokémon in your party."""

    key = "+sheet"
    aliases = ["party"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        self.slot = None
        self.mode = "full"
        if "brief" in self.switches:
            self.mode = "brief"
        if "moves" in self.switches:
            self.mode = "moves"
        arg = self.args.strip()
        if arg.isdigit():
            self.slot = int(arg)

    def func(self):
        caller = self.caller
        try:
            party = caller.storage.get_party() if hasattr(caller.storage, "get_party") else list(caller.storage.active_pokemon.all())
        except OperationalError:
            caller.msg("The game database is out of date. Please run 'evennia migrate'.")
            return
        if not party:
            caller.msg("You have no Pokémon in your party.")
            return

        # if no slot specified show first party member
        slot = self.slot or 1
        if slot < 1 or slot > len(party):
            caller.msg("No Pokémon in that slot.")
            return

        mon = party[slot - 1]
        sheet = display_pokemon_sheet(caller, mon, slot=slot, mode=self.mode)
        caller.msg(sheet)


class CmdSheetPokemon(Command):
    """Show detailed information about one Pokémon in your party."""

    key = "+sheet/pokemon"
    aliases = ["+sheet/pkmn"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        self.slot = None
        arg = self.args.strip()
        if arg.isdigit():
            self.slot = int(arg)

    def func(self):
        caller = self.caller
        if self.slot is None:
            caller.msg("Usage: +sheet/pokemon <slot>")
            return

        party = caller.storage.get_party() if hasattr(caller.storage, "get_party") else list(caller.storage.active_pokemon.all())
        if self.slot < 1 or self.slot > len(party):
            caller.msg("No Pokémon in that slot.")
            return

        mon = party[self.slot - 1]
        if not mon:
            caller.msg("That slot is empty.")
            return

        sheet = display_pokemon_sheet(caller, mon, slot=self.slot)
        caller.msg(sheet)
