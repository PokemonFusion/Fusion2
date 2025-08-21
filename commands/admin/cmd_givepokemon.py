from evennia import Command
from utils.enhanced_evmenu import EnhancedEvMenu

import menus.give_pokemon as give_pokemon


class CmdGivePokemon(Command):
    """Give a Pokémon to a character for debugging.

    Usage:
      @givepokemon <character>
    """

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

        EnhancedEvMenu(
            self.caller,
            give_pokemon,
            startnode="node_start",
            startnode_input=(None, {"target": target}),
        )

