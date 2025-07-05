from evennia import Command
from utils.ansi import ansi
from django.db.utils import OperationalError

class CmdSheet(Command):
    """Display a summary of your Pokémon party."""

    key = "+sheet"
    aliases = ["party"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        caller = self.caller
        try:
            party = list(caller.storage.active_pokemon.all().order_by("id"))
        except OperationalError:
            caller.msg("The game database is out of date. Please run 'evennia migrate'.")
            return
        if not party:
            caller.msg("You have no Pokémon in your party.")
            return

        lines = []
        for idx in range(6):
            mon = party[idx] if idx < len(party) else None
            slot = idx + 1
            if not mon:
                lines.append(f"{slot}. Empty")
                continue

            name = getattr(mon, "name", "Unknown")
            level = getattr(mon, "level", "?")
            gender = getattr(mon, "gender", "?")
            hp = getattr(mon, "hp", getattr(mon, "current_hp", 0))
            max_hp = getattr(mon, "max_hp", getattr(mon, "max_hp", 0))
            status = getattr(mon, "status", "") or ""

            stats = getattr(mon, "stats", {}) or {}
            atk = stats.get("atk") or stats.get("attack") or "?"
            defe = stats.get("def") or stats.get("def_") or "?"
            spd = stats.get("spd") or stats.get("speed") or "?"
            spatk = stats.get("spatk") or stats.get("spa") or "?"
            spdef = stats.get("spdef") or stats.get("spd_def") or "?"

            moves = getattr(mon, "moves", [])
            move_names = [getattr(m, "name", str(m)) for m in moves]
            movestr = ", ".join(move_names[:3])

            icon = ""
            if hp <= 0 or str(status).lower() in ("fnt", "fainted"):
                icon = ansi.RED("FNT")
            elif str(status).lower().startswith("par"):
                icon = ansi.YELLOW("PAR")
            elif status:
                icon = status

            line = (
                f"{slot}. {name} L{level} {gender} "
                f"HP {hp}/{max_hp} "
                f"{icon} "
                f"ATK:{atk} DEF:{defe} SPD:{spd} SPA:{spatk} SPDEF:{spdef} "
                f"{movestr}"
            )
            lines.append(line.strip())

        caller.msg("\n".join(lines))


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

        party = list(caller.storage.active_pokemon.all().order_by("id"))
        if self.slot < 1 or self.slot > len(party):
            caller.msg("No Pokémon in that slot.")
            return

        mon = party[self.slot - 1]
        if not mon:
            caller.msg("That slot is empty.")
            return

        name = getattr(mon, "name", "Unknown")
        level = getattr(mon, "level", "?")
        gender = getattr(mon, "gender", "?")
        pid = getattr(mon, "id", getattr(mon, "unique_id", "?"))
        types = getattr(mon, "types", getattr(mon, "type", []))
        if isinstance(types, (list, tuple)):
            types = "/".join(types)
        ability = getattr(mon, "ability", "?")
        nature = getattr(mon, "nature", "?")
        hp = getattr(mon, "hp", getattr(mon, "current_hp", 0))
        max_hp = getattr(mon, "max_hp", getattr(mon, "max_hp", 0))
        status = getattr(mon, "status", "") or "OK"
        held = getattr(mon, "held_item", "None")
        friendship = getattr(mon, "friendship", "?")
        exp = getattr(mon, "experience", getattr(mon, "exp", 0))
        exp_to = getattr(mon, "exp_to_next", getattr(mon, "exp_to_next_level", 1)) or 1
        stats = getattr(mon, "stats", {}) or {}
        atk = stats.get("atk") or stats.get("attack") or "?"
        defe = stats.get("def") or stats.get("def_") or "?"
        spd = stats.get("spd") or stats.get("speed") or "?"
        spatk = stats.get("spatk") or stats.get("spa") or "?"
        spdef = stats.get("spdef") or stats.get("spd_def") or "?"
        moves = getattr(mon, "moves", [])

        # HP bar
        bar_len = 20
        hp_ratio = 0
        if max_hp:
            hp_ratio = max(0.0, min(1.0, hp / max_hp))
        filled = int(bar_len * hp_ratio)
        if hp_ratio > 0.5:
            bar_color = ansi.GREEN
        elif hp_ratio > 0.25:
            bar_color = ansi.YELLOW
        else:
            bar_color = ansi.RED
        hp_bar = bar_color("█" * filled + " " * (bar_len - filled))

        # EXP bar
        exp_ratio = 0
        if exp_to:
            exp_ratio = max(0.0, min(1.0, exp / exp_to))
        exp_filled = int(bar_len * exp_ratio)
        exp_bar = ansi.CYAN("█" * exp_filled + " " * (bar_len - exp_filled))

        lines = [
            f"|w{name}|n Lv{level} ({gender}) ID:{pid}",
            f"Type: {types}",
            f"Ability: {ability}    Nature: {nature}",
            f"HP: {hp}/{max_hp} {hp_bar}",
            f"ATK:{atk} DEF:{defe} SPD:{spd} SPA:{spatk} SPDEF:{spdef}",
            f"Status: {status}    Held: {held}",
            f"Friendship: {friendship}",
            f"EXP: {exp}/{exp_to} {exp_bar}",
            "Moves:",
        ]

        for mv in moves:
            mname = getattr(mv, "name", str(mv))
            pp = getattr(mv, "pp", getattr(mv, "current_pp", None))
            max_pp = getattr(mv, "max_pp", None)
            if pp is not None and max_pp is not None:
                lines.append(f"  {mname} ({pp}/{max_pp} PP)")
            elif pp is not None:
                lines.append(f"  {mname} ({pp} PP)")
            else:
                lines.append(f"  {mname}")

        caller.msg("\n".join(lines))
