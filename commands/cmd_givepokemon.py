from evennia import Command
from evennia.utils.evmenu import EvMenu

import menus.give_pokemon as give_pokemon


class CmdGivePokemon(Command):
    """Give a Pokemon to a character for debugging."""

    key = "@givepokemon"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        """Launch the give pokemon menu."""
        if not self.args:
            self.caller.msg("Usage: @givepokemon <character>")
            return

        target = self.caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        if not target.is_typeclass("evennia.objects.objects.DefaultCharacter", exact=False):
            self.caller.msg("You can only give Pokémon to characters.")
            return

        if target.storage.active_pokemon.count() >= 6:
            self.caller.msg(f"{target.key}'s party is already full.")
            return

        EvMenu(self.caller, give_pokemon, startnode="node_start", target=target)

