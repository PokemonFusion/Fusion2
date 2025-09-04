"""Commands for viewing trainer and Pokémon information."""

from evennia import Command
from types import SimpleNamespace

from pokemon.helpers.pokemon_helpers import get_max_hp
from pokemon.models.stats import level_for_exp
from utils.display import display_pokemon_sheet, display_trainer_sheet
from utils.display_helpers import get_status_effects
from utils.xp_utils import get_display_xp


class CmdSheet(Command):
    """Display information about your trainer character.

    Usage:
      +sheet [brief]
    """

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
        """Execute the command."""
        caller = self.caller
        sheet = display_trainer_sheet(caller)
        caller.msg(sheet)


class CmdSheetPokemon(Command):
    """Show info about Pokémon in your party.

    Usage:
      +sheet/pokemon [<slot>|all] [/brief|/moves|/full]

    Examples:
      +sheet/pokemon                (list party w/ one-liners)
      +sheet/pokemon 1              (full sheet for slot 1)
      +sheet/pokemon/brief 2        (brief view for slot 2)
      +sheet/pokemon/moves 3        (moves-focused view for slot 3)
      +sheet/pokemon/all            (full sheets for all occupied slots)
    """

    key = "+sheet/pokemon"
    aliases = ["+sheet/pkmn"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        """Parse arguments and switches."""
        self.slot = None
        self.show_all = False
        self.mode = "full"
        switches = getattr(self, "switches", [])
        if "brief" in switches:
            self.mode = "brief"
        if "moves" in switches:
            self.mode = "moves"
        if "full" in switches:
            self.mode = "full"
        arg = self.args.strip().lower()
        if arg == "all":
            self.show_all = True
        elif arg.isdigit():
            self.slot = int(arg)

    def func(self):
        """Execute the command."""
        caller = self.caller

        # Get party; normalize to a fixed-size list (6) with None for empties
        if hasattr(caller.storage, "get_party"):
            party = list(caller.storage.get_party()) or []
        else:
            party = list(caller.storage.active_pokemon.all())

        if len(party) < 6:
            party = party + [None] * (6 - len(party))
        elif len(party) > 6:
            party = party[:6]

        trainer = getattr(caller, "trainer", None)
        fusion_species = getattr(getattr(caller, "db", None), "fusion_species", None)
        fusion_id = getattr(getattr(caller, "db", None), "fusion_id", None)
        if fusion_species or fusion_id:
            hp_val = getattr(caller.db, "hp", None)
            stats = getattr(caller.db, "stats", None)
            stats = stats.copy() if isinstance(stats, dict) else {}
            try:
                search = list(caller.storage.active_pokemon.all())
            except Exception:
                search = []
            fused = None
            if fusion_id:
                fused = next(
                    (
                        mon
                        for mon in search
                        if str(getattr(mon, "unique_id", "")) == str(fusion_id)
                    ),
                    None,
                )
            if not fused and fusion_species:
                fused = next(
                    (
                        mon
                        for mon in search
                        if getattr(getattr(mon, "species", None), "name", getattr(mon, "species", None))
                        == fusion_species
                    ),
                    None,
                )
            if fused:
                fusion_id = fusion_id or getattr(fused, "unique_id", None)
                if not fusion_species:
                    fusion_species = getattr(
                        getattr(fused, "species", None), "name", getattr(fused, "species", None)
                    )
                if not stats:
                    stats = getattr(fused, "_cached_stats", {}) or {}
                if hp_val is None:
                    hp_val = getattr(fused, "hp", getattr(fused, "current_hp", None))
            if hp_val is None:
                hp_val = stats.get("hp", 0)
            if stats.get("hp") is None:
                stats["hp"] = hp_val
            level_val = getattr(caller.db, "level", None)
            exp_val = getattr(caller.db, "total_exp", None)
            if fused:
                if level_val is None:
                    level_val = getattr(fused, "level", None)
                if exp_val is None:
                    exp_val = getattr(fused, "total_exp", None)
            fusion_mon = SimpleNamespace(
                name=fusion_species,
                species=fusion_species,
                ability=getattr(caller.db, "fusion_ability", None),
                nature=getattr(caller.db, "fusion_nature", None),
                gender=getattr(caller.db, "gender", "?"),
                level=level_val,
                total_exp=exp_val,
                hp=hp_val or 0,
            )
            if fusion_id is not None:
                setattr(fusion_mon, "unique_id", fusion_id)
                setattr(fusion_mon, "id", fusion_id)
            if fused:
                for attr in ("activemoveslot_set", "pp_bonuses", "moves", "ivs", "evs"):
                    if hasattr(fused, attr):
                        setattr(fusion_mon, attr, getattr(fused, attr))
                if fused in party:
                    party[party.index(fused)] = None
            setattr(fusion_mon, "_cached_stats", stats)
            setattr(fusion_mon, "_pf2_is_fusion_slot", True)
            setattr(fusion_mon, "_pf2_fusion_owner_name", getattr(caller, "key", ""))
            try:
                empty_idx = party.index(None)
                party[empty_idx] = fusion_mon
            except ValueError:
                if len(party) < 6:
                    party.append(fusion_mon)

        if self.show_all:
            if not party:
                caller.msg("You have no Pokémon in your party.")
                return
            sheets = []
            for idx, mon in enumerate(party, 1):
                if not mon:
                    continue
                sheet = display_pokemon_sheet(caller, mon, slot=idx, mode=self.mode)
                if getattr(mon, "_pf2_is_fusion_slot", False):
                    sheet += "\n|yNote: This slot shows your active Fusion form.|n"
                sheets.append(sheet)
            caller.msg("\n-------\n".join(sheets))
            return

        if self.slot is None:
            if not party:
                caller.msg("You have no Pokémon in your party.")
                return
            lines = ["|wParty Pokémon|n"]
            for idx, mon in enumerate(party, 1):
                if not mon:
                    continue
                level = getattr(mon, "level", None)
                if level is None:
                    xp_val = get_display_xp(mon)
                    growth = getattr(mon, "growth_rate", "medium_fast")
                    level = level_for_exp(xp_val, growth)
                hp = getattr(mon, "hp", getattr(mon, "current_hp", 0))
                max_hp = get_max_hp(mon)
                status = get_status_effects(mon)
                gender = getattr(mon, "gender", "?")
                name = mon.name
                label = ""
                if getattr(mon, "_pf2_is_fusion_slot", False):
                    owner = getattr(mon, "_pf2_fusion_owner_name", "")
                    base = getattr(mon, "species", name)
                    if owner:
                        name = f"{owner} ({base})"
                    label = " (fusion)"
                lines.append(f"{idx}: {name}{label} (Lv {level} HP {hp}/{max_hp} {gender} {status})")
            caller.msg("\n".join(lines))
            return

        if self.slot < 1 or self.slot > len(party):
            caller.msg("No Pokémon in that slot.")
            return

        mon = party[self.slot - 1]
        if not mon:
            caller.msg("That slot is empty.")
            return

        sheet = display_pokemon_sheet(caller, mon, slot=self.slot, mode=self.mode)
        if getattr(mon, "_pf2_is_fusion_slot", False):
            sheet += "\n|yNote: This slot shows your active Fusion form.|n"
        caller.msg(sheet)
