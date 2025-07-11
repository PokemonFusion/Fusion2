from evennia import Command
from django.db.utils import OperationalError
from utils.sheet_display import display_pokemon_sheet, display_trainer_sheet

class CmdSheet(Command):
    """Display information about your trainer character."""

    key = "+sheet"
    aliases = ["party"]
    locks = "cmd:all()"
    help_category = "General"

    def parse(self):
        self.mode = "full"
        self.switches = getattr(self, "switches", [])
        if "brief" in self.switches:
            self.mode = "brief"

    def func(self):
        caller = self.caller
        sheet = display_trainer_sheet(caller)
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
        party = caller.storage.get_party() if hasattr(caller.storage, "get_party") else list(caller.storage.active_pokemon.all())
        if self.slot is None:
            if not party:
                caller.msg("You have no Pokémon in your party.")
                return
            lines = ["|wParty Pokémon|n"]
            for idx, mon in enumerate(party, 1):
                lines.append(f"{idx}: {mon.name} (Lv {getattr(mon, 'level', '?')})")
            caller.msg("\n".join(lines))
            return

        if self.slot < 1 or self.slot > len(party):
            caller.msg("No Pokémon in that slot.")
            return

        mon = party[self.slot - 1]
        if not mon:
            caller.msg("That slot is empty.")
            return

        sheet = display_pokemon_sheet(caller, mon, slot=self.slot)
        caller.msg(sheet)
