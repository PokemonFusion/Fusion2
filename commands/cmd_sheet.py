from evennia import Command
from django.db.utils import OperationalError
from utils.sheet_display import (
    display_pokemon_sheet,
    display_trainer_sheet,
    get_status_effects,
)
from pokemon.utils.pokemon_helpers import get_max_hp
from utils.xp_utils import get_display_xp
from pokemon.stats import level_for_exp

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
        self.show_all = False
        arg = self.args.strip().lower()
        if arg == "all":
            self.show_all = True
        elif arg.isdigit():
            self.slot = int(arg)

    def func(self):
        caller = self.caller
        party = caller.storage.get_party() if hasattr(caller.storage, "get_party") else list(caller.storage.active_pokemon.all())
        if self.show_all:
            if not party:
                caller.msg("You have no Pokémon in your party.")
                return
            sheets = []
            for idx, mon in enumerate(party, 1):
                if not mon:
                    continue
                sheets.append(display_pokemon_sheet(caller, mon, slot=idx))
            caller.msg("\n-------\n".join(sheets))
            return

        if self.slot is None:
            if not party:
                caller.msg("You have no Pokémon in your party.")
                return
            lines = ["|wParty Pokémon|n"]
            for idx, mon in enumerate(party, 1):
                level = getattr(mon, "level", None)
                if level is None:
                    xp_val = get_display_xp(mon)
                    growth = getattr(mon, "growth_rate", "medium_fast")
                    level = level_for_exp(xp_val, growth)
                hp = getattr(mon, "hp", getattr(mon, "current_hp", 0))
                max_hp = get_max_hp(mon)
                status = get_status_effects(mon)
                gender = getattr(mon, "gender", "?")
                lines.append(
                    f"{idx}: {mon.name} (Lv {level} HP {hp}/{max_hp} {gender} {status})"
                )
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
