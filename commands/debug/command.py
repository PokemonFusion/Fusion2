from evennia import Command


def heal_party(char):
    """Heal all active Pokemon for the given character."""
    storage = getattr(char, "storage", None)
    if not storage:
        return
    party = storage.get_party() if hasattr(storage, "get_party") else list(storage.active_pokemon.all())
    for mon in party:
        if hasattr(mon, "heal"):
            mon.heal()

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
        pokemon_id = self.args.strip()
        pokemon = self.caller.get_pokemon_by_id(pokemon_id)
        if pokemon:
            self.caller.msg(str(pokemon))
        else:
            self.caller.msg(f"No Pokémon found with ID {pokemon_id}.")


class CmdUseMove(Command):
    """Use a Pokémon move in a simple battle simulation.

    Usage:
      usemove <move> <attacker> <target>
    """

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

        inst = getattr(self.caller.ndb, "battle_instance", None)
        if inst:
            inst.queue_move(move_name, caller=self.caller)
            return

        import copy

        from pokemon.battle import damage_calc
        from pokemon.dex import MOVEDEX, POKEDEX, Move

        # MOVEDEX keys are stored in lowercase
        movedata = MOVEDEX.get(move_name.lower())
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


class CmdChooseStarter(Command):
    """Choose your first Pokémon.

    Usage:
      choosestarter <pokemon>
    """

    key = "choosestarter"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: choosestarter <pokemon>")
            return
        result = self.caller.choose_starter(self.args.strip())
        self.caller.msg(result)


class CmdSpoof(Command):
    """
    Emit text to the current room without attribution.

    Usage:
        spoof <message>
        @emit <message>
    """

    key = "spoof"
    aliases = ["@emit"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        """Send the raw message to the room."""
        message = self.args.strip()
        if not message:
            self.caller.msg("Usage: spoof <message>")
            return
        location = self.caller.location
        if not location:
            self.caller.msg("You have no location to spoof from.")
            return
        location.msg_contents(message)
class CmdExpShare(Command):
    """Toggle the EXP Share effect for your party.

    Usage:
      +expshare
    """

    key = "+expshare"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        current = bool(self.caller.db.exp_share)
        if current:
            self.caller.db.exp_share = False
            self.caller.msg("EXP Share is turned OFF.")
        else:
            self.caller.db.exp_share = True
            self.caller.msg("EXP Share is turned ON.")


class CmdHeal(Command):
    """Heal your Pokémon party at a Pokémon Center.

    Usage:
      +heal
    """

    key = "+heal"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        location = self.caller.location
        if not (location and location.db.is_pokemon_center):
            self.caller.msg("You must be at a Pokémon Center to heal.")
            return
        heal_party(self.caller)
        self.caller.msg("Your Pokémon have been fully healed.")


class CmdAdminHeal(Command):
    """Heal another player's Pokémon party.

    Usage:
      +adminheal [<player>]
    """

    key = "+adminheal"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def parse(self):
        self.target_name = self.args.strip()

    def func(self):
        target = self.caller
        if self.target_name:
            target = self.caller.search(self.target_name, global_search=True)
            if not target:
                return
        heal_party(target)
        if target.location:
            target.location.msg_contents(
                f"{self.caller.key} heals {target.key}'s Pokémon party.")
        self.caller.msg(f"{target.key}'s Pokémon have been healed.")
        if target != self.caller:
            target.msg("Your Pokémon have been healed by an admin.")

