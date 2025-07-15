from evennia.commands.default.account import CmdCharCreate as DefaultCmdCharCreate
from evennia import Command, search_account
from django.conf import settings

class CmdCharCreate(DefaultCmdCharCreate):
    """Create a new character with a maximum-per-account limit.

    Usage:
      charcreate <name>
    """

    help_category = "General"

    def func(self):
        account = self.account
        max_chars = settings.MAX_NR_CHARACTERS
        if max_chars is not None and len(account.characters) >= max_chars:
            self.msg(f"You already have the maximum number of characters ({max_chars}).")
            return
        super().func()

class CmdAlts(Command):
    """List all characters for an account.

    Usage:
      @alts <account>
    """

    key = "@alts"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.msg("Usage: @alts <account>")
            return
        results = search_account(self.args.strip(), exact=True)
        account = results[0] if results else None
        if not account:
            self.msg("No matching account found.")
            return
        names = ", ".join(char.key for char in account.characters) if account.characters else "None"
        self.msg(f"Characters for {account.key}: {names}")

class CmdTradePokemon(Command):
    """Trade a Pokémon with another character.

    Usage:
      tradepokemon <pokemon_id>=<character>
    """

    key = "tradepokemon"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: tradepokemon <pokemon_id>=<character>")
            return
        pid, target_name = [part.strip() for part in self.args.split("=", 1)]
        target = self.caller.search(target_name)
        if not target:
            return
        if target.account == self.caller.account:
            self.caller.msg("You cannot trade items between your own characters.")
            return
        pokemon = self.caller.get_pokemon_by_id(pid)
        if not pokemon:
            self.caller.msg("No such Pokémon.")
            return
        if pokemon in self.caller.storage.active_pokemon.all():
            self.caller.storage.remove_active_pokemon(pokemon)
            target.storage.add_active_pokemon(pokemon)
        elif pokemon in self.caller.storage.stored_pokemon.all():
            self.caller.storage.stored_pokemon.remove(pokemon)
            target.storage.stored_pokemon.add(pokemon)
        else:
            self.caller.msg("You don't have that Pokémon.")
            return
        name = pokemon.nickname or pokemon.species
        self.caller.msg(f"You traded {name} to {target.key}.")
        target.msg(f"{self.caller.key} traded {name} to you.")

