from evennia import Command
from utils.pokemon_utils import create_pokemon

class CmdCreatePokemon(Command):
    """
    Create a new Pokémon for a player.

    Usage:
      +createpokemon <name>

    This will create a Pokémon with the given name for the player.
    """
    key = "+createpokemon"
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +createpokemon <name>")
            return
        
        name = self.args.strip()
        try:
            pokemon = create_pokemon(name, owner=self.caller)
            self.caller.msg(f"Pokémon {name} created with ID {pokemon.db.pokemon_id}.")
        except ValueError as e:
            self.caller.msg(str(e))

class CmdShowPokemon(Command):
    """
    Show a player's Pokémon.

    Usage:
      +showpokemon

    This will list all Pokémon owned by the player.
    """
    key = "+showpokemon"
    locks = "cmd:all()"

    def func(self):
        pokemons = [obj for obj in self.caller.contents if obj.is_typeclass("typeclasses.pokemon.Pokemon")]
        if not pokemons:
            self.caller.msg("You do not own any Pokémon.")
            return
        
        message = "Your Pokémon:\n"
        for pokemon in pokemons:
            message += f"{pokemon.db.pokemon_id}: {pokemon.key} (Level {pokemon.db.level})\n"
        self.caller.msg(message)
