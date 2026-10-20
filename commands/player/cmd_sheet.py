"""Commands for viewing trainer and Pokémon information."""

import shlex
from typing import Optional

from evennia import Command

from pokemon.helpers.party_helpers import get_party_slots
from utils.display import display_pokemon_sheet, display_trainer_sheet


def _parse_slash_switches(command):
    """Extract Evennia-style /switches for Command subclasses."""

    switches = []
    for switch in getattr(command, "switches", []) or []:
        switches.extend(part for part in str(switch).lower().split("/") if part)

    raw_args = (command.args or "").strip()
    if raw_args.startswith("/") and len(raw_args) > 1:
        switch_text, _, raw_args = raw_args[1:].partition(" ")
        switches.extend(part for part in switch_text.lower().split("/") if part)
        raw_args = raw_args.strip()

    command.switches = switches
    command.args = raw_args
    return set(switches)


def _party_slots(caller):
    """Use canonical slot positions for list displays and numbered sheets."""
    return get_party_slots(caller)


class CmdSheet(Command):
    """Display your trainer overview, inventory, or a party slot.

    Usage:
      +sheet                     - full trainer card
      +sheet/brief               - compact snapshot
      +sheet/inv [page]          - paginated inventory
      +sheet/inv cols <n>        - inventory with explicit columns (1-4)
      +sheet/inv find <text>     - inventory filtered by name
      +sheet/inv/cat             - grouped inventory view
      +sheet <slot>              - Pokémon sheet for a party slot (if available)
      +sheet/sr or +sheet/nosr   - toggle screen-reader formatting

    Examples:
      +sheet
      +sheet/brief
      +sheet/inv find potion

    Notes:
      Use +party when you only want the Pokemon in your active party.
    """

    key = "+sheet"
    aliases = ["party", "+trainer"]
    locks = "cmd:all()"
    help_category = "General"

    def parse(self):
        """Parse switches and arguments for trainer, inventory, or slot views."""

        switches = _parse_slash_switches(self)

        self.mode = "brief" if "brief" in switches else "full"
        self.view_inventory = "inv" in switches and "cat" not in switches and "inv/cat" not in switches
        self.view_inventory_by_category = "inv/cat" in switches or ("inv" in switches and "cat" in switches)
        self.screen_reader_switch = "sr" in switches
        self.disable_screen_reader = "nosr" in switches or ("off" in switches and "sr" in switches)

        self.page = 1
        self.cols: Optional[int] = None
        self.find = ""
        self.slot: Optional[int] = None

        raw_args = (self.args or "").strip()
        tokens: list[str] = []
        if raw_args:
            try:
                tokens = shlex.split(raw_args)
            except ValueError:
                tokens = raw_args.split()

        if self.view_inventory and tokens and tokens[0].isdigit():
            try:
                self.page = max(1, int(tokens[0]))
                tokens = tokens[1:]
            except (TypeError, ValueError):
                pass
        elif not self.view_inventory and not self.view_inventory_by_category and tokens and tokens[0].isdigit():
            try:
                self.slot = int(tokens[0])
                tokens = tokens[1:]
            except (TypeError, ValueError):
                self.slot = None

        idx = 0
        while idx < len(tokens):
            token = tokens[idx]
            lower = token.lower()
            if lower == "cols" and idx + 1 < len(tokens):
                try:
                    value = int(tokens[idx + 1])
                    self.cols = max(1, min(4, value))
                except (TypeError, ValueError):
                    self.cols = None
                idx += 2
                continue
            if lower == "find":
                self.find = " ".join(tokens[idx + 1 :]).strip()
                break
            idx += 1

    def func(self):
        """Execute the command."""
        caller = self.caller
        if self.screen_reader_switch:
            caller.attributes.add("sheet_screen_reader", True)
        if self.disable_screen_reader:
            caller.attributes.add("sheet_screen_reader", False)

        find_text = self.find or ""

        if self.view_inventory_by_category:
            try:
                from utils.display import display_inventory_by_category

                caller.msg(
                    display_inventory_by_category(
                        caller,
                        cols=self.cols or 3,
                        find=find_text,
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive for runtime errors
                caller.msg(f"|rInventory (category) error:|n {exc}")
            return

        if self.view_inventory:
            try:
                from utils.display import display_full_inventory

                caller.msg(
                    display_full_inventory(
                        caller,
                        page=self.page,
                        cols=self.cols or 3,
                        find=find_text,
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive for runtime errors
                caller.msg(f"|rInventory error:|n {exc}")
            return

        if isinstance(self.slot, int):
            try:
                party = _party_slots(caller)
            except Exception:  # pragma: no cover - best effort compatibility
                party = []

            if not any(party):
                caller.msg("You have no Pokémon in your party.")
                return
            if self.slot < 1 or self.slot > len(party):
                caller.msg("No Pokémon in that slot.")
                return

            pokemon = party[self.slot - 1]
            if not pokemon:
                caller.msg("That slot is empty.")
                return

            try:
                sheet = display_pokemon_sheet(caller, pokemon, slot=self.slot, mode=self.mode)
            except Exception as exc:  # pragma: no cover - defensive for runtime errors
                caller.msg(f"|rPokémon sheet error:|n {exc}")
                return

            caller.msg(sheet)
            return

        try:
            sheet = display_trainer_sheet(caller, mode=self.mode)
        except TypeError:  # pragma: no cover - compatibility with legacy signature
            sheet = display_trainer_sheet(caller)
        caller.msg(sheet)


class CmdSheetPokemon(Command):
    """Show info about Pokemon in your active party.

    Usage:
      +party [<slot>||all] [/brief||/moves||/full]
      +sheet/pokemon [<slot>||all] [/brief||/moves||/full]

    Examples:
      +party                 List your party with two-line health cards.
      +party 1               Show the full sheet for slot 1.
      +party/brief 2         Show a brief view for slot 2.
      +party/moves 3         Show a moves-focused view for slot 3.
      +party/all             Show full sheets for all occupied slots.
      +party fusion          Show your active Fusion, including with a full party.

    Notes:
      Party slots run from 1 to 6; gaps retain their numbers.
      Fusion uses a free slot, or the fusion selector when all six are full.
      LEAD marks the first conscious member in your configured battle order.
    """

    key = "+party"
    aliases = ["+sheet/pokemon", "+sheet/pkmn"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        """Parse arguments and switches."""
        self.slot = None
        self.show_all = False
        self.mode = "full"
        switches = _parse_slash_switches(self)
        if "brief" in switches:
            self.mode = "brief"
        if "moves" in switches:
            self.mode = "moves"
        if "full" in switches:
            self.mode = "full"
        arg = self.args.strip().lower()
        if arg == "all" or "all" in switches:
            self.show_all = True
        elif arg == "fusion":
            self.slot = "fusion"
        elif arg.isdigit():
            self.slot = int(arg)

    def func(self):
        """Display party cards or the selected member's detailed sheet."""
        from utils.party_view import PartyView

        caller = self.caller
        view = PartyView(caller)
        if self.slot is None and not self.show_all:
            caller.msg(view.render())
            return
        if not view.entries:
            caller.msg("You have no Pokémon in your party.")
            return
        if self.show_all:
            entries = view.entries
        else:
            entry = view.select(self.slot)
            if entry is None:
                if self.slot == "fusion":
                    caller.msg("You have no active Fusion form.")
                elif self.slot < 1 or self.slot > 6:
                    caller.msg("No Pokémon in that slot.")
                else:
                    caller.msg("That slot is empty.")
                return
            entries = [entry]
        sheets = []
        for entry in entries:
            sheet = display_pokemon_sheet(caller, entry.pokemon, slot=entry.selector, mode=self.mode)
            if entry.is_fusion:
                sheet += "\n|yNote: This slot shows your active Fusion form.|n"
            sheets.append(sheet)
        caller.msg("\n-------\n".join(sheets))
