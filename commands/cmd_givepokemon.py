from evennia import Command, search_object
from pokemon.utils.enhanced_evmenu import EnhancedEvMenu

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

        matches = search_object(self.args.strip())
        if not matches:
            self.caller.msg("No such character.")
            return
        target = matches[0]
        if not target.is_typeclass("evennia.objects.objects.DefaultCharacter", exact=False):
            self.caller.msg("You can only give Pokémon to characters.")
            return

        EnhancedEvMenu(
            self.caller,
            give_pokemon,
            startnode="node_start",
            startnode_input=(None, {"target": target}),
        )

