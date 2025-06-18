from evennia import Command

class CmdShowPokemonOnUser(Command):
    """
    Show Pokémon on user

    Usage:
        showpokemononuser

    Shows the Pokémon currently on the user.
    """

    key = "showpokemononuser"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        self.caller.msg(f"Pokémon on {self.caller.key}:")
        self.caller.msg(self.caller.show_pokemon_on_user())

class CmdShowPokemonInStorage(Command):
    """
    Show Pokémon in storage

    Usage:
        showpokemoninstorage

    Shows the Pokémon currently in storage.
    """

    key = "showpokemoninstorage"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        self.caller.msg(f"Pokémon in storage for {self.caller.key}:")
        self.caller.msg(self.caller.show_pokemon_in_storage())

class CmdAddPokemonToUser(Command):
    """
    Add a Pokémon to the user

    Usage:
        addpokemontouser <name> <level> <type>

    Adds a Pokémon to the user's active Pokémon list.
    """

    key = "addpokemontouser"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: addpokemontouser <name> <level> <type>")
            return
        try:
            name, level, type_ = self.args.split()
            level = int(level)
            self.caller.add_pokemon_to_user(name, level, type_)
            self.caller.msg(f"Added {name} (Level {level}, Type: {type_}) to your active Pokémon.")
        except ValueError:
            self.caller.msg("Usage: addpokemontouser <name> <level> <type>")

class CmdAddPokemonToStorage(Command):
    """
    Add a Pokémon to the storage

    Usage:
        addpokemontostorage <name> <level> <type>

    Adds a Pokémon to the user's storage.
    """

    key = "addpokemontostorage"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: addpokemontostorage <name> <level> <type>")
            return
        try:
            name, level, type_ = self.args.split()
            level = int(level)
            self.caller.add_pokemon_to_storage(name, level, type_)
            self.caller.msg(f"Added {name} (Level {level}, Type: {type_}) to your storage.")
        except ValueError:
            self.caller.msg("Usage: addpokemontostorage <name> <level> <type>")

class CmdGetPokemonDetails(Command):
    """
    Get details of a Pokémon by ID

    Usage:
        getpokemondetails <pokemon_id>

    Retrieves details of a Pokémon by its ID.
    """

    key = "getpokemondetails"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: getpokemondetails <pokemon_id>")
            return
        try:
            pokemon_id = int(self.args.strip())
            pokemon = self.caller.get_pokemon_by_id(pokemon_id)
            if pokemon:
                self.caller.msg(str(pokemon))
            else:
                self.caller.msg(f"No Pokémon found with ID {pokemon_id}.")
        except ValueError:
            self.caller.msg("Usage: getpokemondetails <pokemon_id>")


class CmdUseMove(Command):
    """Use a Pokémon move in a simple battle simulation."""

    key = "usemove"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: usemove <move> <attacker> <target>")
            return
        try:
            move_name, attacker_name, target_name = self.args.split()
        except ValueError:
            self.caller.msg("Usage: usemove <move> <attacker> <target>")
            return

        from pokemon.dex import MOVEDEX, POKEDEX, Move
        from pokemon.battle import damage_calc
        import copy

        movedata = MOVEDEX.get(move_name.capitalize())
        if not movedata:
            self.caller.msg(f"Unknown move '{move_name}'.")
            return

        attacker = POKEDEX.get(attacker_name.lower())
        target = POKEDEX.get(target_name.lower())
        if not attacker or not target:
            self.caller.msg("Unknown attacker or target Pokémon name.")
            return

        move = Move.from_dict(move_name.capitalize(), movedata)
        att = copy.deepcopy(attacker)
        tgt = copy.deepcopy(target)
        att.current_hp = att.base_stats.hp
        tgt.current_hp = tgt.base_stats.hp

        result = damage_calc(att, tgt, move)
        total_dmg = sum(result.debug.get("damage", []))
        tgt.current_hp = max(0, tgt.current_hp - total_dmg)
        if tgt.current_hp == 0:
            result.fainted.append(tgt.name)

        out = result.text
        out.append(f"{tgt.name} has {tgt.current_hp} HP remaining.")
        if getattr(tgt, "status", None):
            out.append(f"{tgt.name} is now {tgt.status}.")
        self.caller.msg("\n".join(out))

class CmdHunt(Command):
    """Search for a wild Pokémon or a trainer to battle."""

    key = "+hunt"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        from pokemon.battle.battleinstance import BattleInstance

        if self.caller.ndb.get("battle_instance"):
            self.caller.msg("You are already engaged in a battle.")
            return

        battle = BattleInstance(self.caller)
        battle.start()

