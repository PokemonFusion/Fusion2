"""Admin command for editing room spawn tables."""
from __future__ import annotations

from evennia import Command
from evennia.utils.evmenu import EvMenu


class CmdSpawns(Command):
    """Open a menu to edit the current room's spawn table."""

    key = "+spawns"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        caller = self.caller

        def _menunode_main(caller, raw_string, **kwargs):
            table = caller.location.db.spawn_table or []
            text = "Current spawns:\n"
            for entry in table:
                text += f"{entry['species']} ({entry.get('rarity','common')})\n"
            options = (
                {"desc": "Add spawn", "goto": "add_spawn"},
                {"desc": "Quit", "goto": "quit"},
            )
            return text, options

        def _menunode_add_spawn(caller, raw_string, **kwargs):
            caller.msg("Enter species name:")
            return "get_species", {}

        def _menunode_get_species(caller, raw_string, **kwargs):
            kwargs["species"] = raw_string.strip()
            caller.msg("Enter rarity (common/uncommon/rare/etc):")
            return "get_rarity", kwargs

        def _menunode_get_rarity(caller, raw_string, **kwargs):
            kwargs["rarity"] = raw_string.strip() or "common"
            caller.msg("Enter tiers separated by space:")
            return "get_tiers", kwargs

        def _menunode_get_tiers(caller, raw_string, **kwargs):
            kwargs["tiers"] = raw_string.strip().split()
            caller.msg("Enter generations separated by space:")
            return "get_gens", kwargs

        def _menunode_get_gens(caller, raw_string, **kwargs):
            kwargs["generations"] = raw_string.strip().split()
            table = caller.location.db.spawn_table or []
            table.append(
                {
                    "species": kwargs.get("species"),
                    "rarity": kwargs.get("rarity"),
                    "tiers": kwargs.get("tiers", []),
                    "generations": kwargs.get("generations", []),
                }
            )
            caller.location.db.spawn_table = table
            caller.msg("Spawn added.")
            return "main", {}

        def _menunode_quit(caller, raw_string, **kwargs):
            caller.msg("Closing spawn editor.")
            return None, None

        menu_nodes = {
            "main": _menunode_main,
            "add_spawn": _menunode_add_spawn,
            "get_species": _menunode_get_species,
            "get_rarity": _menunode_get_rarity,
            "get_tiers": _menunode_get_tiers,
            "get_gens": _menunode_get_gens,
            "quit": _menunode_quit,
        }

        EvMenu(caller, menu_nodes, startnode="main")

