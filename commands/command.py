from evennia import Command
from pokemon.generation import generate_pokemon
from pokemon.stats import calculate_stats


def _get_stats_from_data(pokemon):
    """Return calculated stats based on stored data."""
    data = getattr(pokemon, "data", {}) or {}
    if not data and hasattr(pokemon, "ivs"):
        ivs = {
            "hp": pokemon.ivs[0],
            "atk": pokemon.ivs[1],
            "def": pokemon.ivs[2],
            "spa": pokemon.ivs[3],
            "spd": pokemon.ivs[4],
            "spe": pokemon.ivs[5],
        }
        evs = {
            "hp": pokemon.evs[0],
            "atk": pokemon.evs[1],
            "def": pokemon.evs[2],
            "spa": pokemon.evs[3],
            "spd": pokemon.evs[4],
            "spe": pokemon.evs[5],
        }
        nature = getattr(pokemon, "nature", "Hardy")
        name = getattr(pokemon, "species", getattr(pokemon, "name", ""))
        level = getattr(pokemon, "level", 1)
    else:
        ivs = data.get("ivs", {})
        evs = data.get("evs", {})
        nature = data.get("nature", "Hardy")
        name = getattr(pokemon, "name", getattr(pokemon, "species", ""))
        level = getattr(pokemon, "level", 1)
    try:
        return calculate_stats(name, level, ivs, evs, nature)
    except Exception:
        inst = generate_pokemon(name, level=level)
        return {
            "hp": inst.stats.hp,
            "atk": inst.stats.atk,
            "def": inst.stats.def_,
            "spa": inst.stats.spa,
            "spd": inst.stats.spd,
            "spe": inst.stats.spe,
        }


def get_max_hp(pokemon) -> int:
    """Return the calculated maximum HP for ``pokemon``."""
    stats = _get_stats_from_data(pokemon)
    return stats.get("hp", 0)


def get_stats(pokemon):
    """Return a dict of calculated stats for ``pokemon``."""
    return _get_stats_from_data(pokemon)


def heal_pokemon(pokemon):
    """Restore a single Pokemon's HP and clear status."""
    max_hp = get_max_hp(pokemon)
    if hasattr(pokemon, "current_hp"):
        pokemon.current_hp = max_hp
    if hasattr(pokemon, "status"):
        pokemon.status = ""
    try:
        pokemon.save()
    except Exception:
        pass


def heal_party(char):
    """Heal all active Pokemon for the given character."""
    storage = getattr(char, "storage", None)
    if not storage:
        return
    for mon in storage.active_pokemon.all():
        heal_pokemon(mon)

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

        inst = self.caller.ndb.get("battle_instance")
        if inst:
            inst.queue_move(move_name)
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


class CmdChooseStarter(Command):
    """Choose your first Pokémon."""

    key = "choosestarter"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: choosestarter <pokemon>")
            return
        result = self.caller.choose_starter(self.args.strip())
        self.caller.msg(result)


class CmdDepositPokemon(Command):
    """Deposit a Pokémon into a storage box."""

    key = "deposit"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        parts = self.args.split()
        if not parts:
            self.caller.msg("Usage: deposit <pokemon_id> [box]")
            return
        pid = parts[0]
        try:
            box = int(parts[1]) if len(parts) > 1 else 1
        except ValueError:
            self.caller.msg("Usage: deposit <pokemon_id> [box]")
            return
        self.caller.msg(self.caller.deposit_pokemon(pid, box))


class CmdWithdrawPokemon(Command):
    """Withdraw a Pokémon from a storage box."""

    key = "withdraw"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        parts = self.args.split()
        if not parts:
            self.caller.msg("Usage: withdraw <pokemon_id> [box]")
            return
        pid = parts[0]
        try:
            box = int(parts[1]) if len(parts) > 1 else 1
        except ValueError:
            self.caller.msg("Usage: withdraw <pokemon_id> [box]")
            return
        self.caller.msg(self.caller.withdraw_pokemon(pid, box))


class CmdShowBox(Command):
    """Show the contents of a storage box."""

    key = "showbox"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        try:
            index = int(self.args.strip() or "1")
        except ValueError:
            self.caller.msg("Usage: showbox <box_number>")
            return
        self.caller.msg(self.caller.show_box(index))


class CmdSetHoldItem(Command):
    """Give one of your active Pokémon a held item."""

    key = "setholditem"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: setholditem <slot>=<item>")
            return

        slot_str, item_name = [p.strip() for p in self.args.split("=", 1)]

        try:
            slot = int(slot_str)
        except ValueError:
            self.caller.msg("Slot must be a number between 1 and 6.")
            return

        pokemon = self.caller.get_active_pokemon_by_slot(slot)
        if not pokemon:
            self.caller.msg("No Pokémon in that slot.")
            return

        item = self.caller.search(item_name, location=self.caller)
        if not item:
            return

        pokemon.held_item = item.key
        pokemon.save()
        item.delete()

        self.caller.msg(f"{pokemon.name} is now holding {item.key}.")


class CmdChargenInfo(Command):
    """Show chargen details and active Pokémon."""

    key = "chargeninfo"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        char = self.caller
        lines = ["|wCharacter Info|n"]
        lines.append(f"  Gender: {char.db.gender or 'Unset'}")
        if char.db.favored_type:
            lines.append(f"  Favored type: {char.db.favored_type}")
        if char.db.fusion_species:
            lines.append(f"  Fusion species: {char.db.fusion_species}")
        if char.db.fusion_ability:
            lines.append(f"  Fusion ability: {char.db.fusion_ability}")
        storage = getattr(char, "storage", None)
        if storage:
            mons = list(storage.active_pokemon.all())
            if mons:
                lines.append("  Active Pokémon:")
                for mon in mons:
                    lines.append(
                        f"    {mon.name} (Lv {mon.level}, Ability: {mon.ability})"
                    )
            else:
                lines.append("  Active Pokémon: None")
        else:
            lines.append("  No storage data.")
        char.msg("\n".join(lines))


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


class CmdInventory(Command):
    """Show items in your inventory."""

    key = "inventory"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        self.caller.msg(self.caller.list_inventory())


class CmdAddItem(Command):
    """Add an item to your inventory."""

    key = "additem"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        parts = self.args.split()
        if len(parts) != 2:
            self.caller.msg("Usage: additem <item> <amount>")
            return
        item = parts[0]
        try:
            qty = int(parts[1])
        except ValueError:
            self.caller.msg("Usage: additem <item> <amount>")
            return
        self.caller.add_item(item, qty)
        self.caller.msg(f"Added {qty} x {item}.")


class CmdUseItem(Command):
    """Use an item outside of battle."""

    key = "useitem"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        item_name = self.args.strip()
        if not item_name:
            self.caller.msg("Usage: useitem <item>")
            return
        if not self.caller.has_item(item_name):
            self.caller.msg(f"You do not have any {item_name}.")
            return
        self.caller.remove_item(item_name)
        self.caller.msg(f"You use {item_name}. Nothing happens.")


class CmdEvolvePokemon(Command):
    """Evolve one of your Pokémon if possible."""

    key = "evolve"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        """Attempt to evolve one of the player's Pokémon."""
        parts = self.args.split()
        if not parts:
            self.caller.msg("Usage: evolve <pokemon_id> [item]")
            return

        pid = parts[0]
        item = parts[1] if len(parts) > 1 else None
        pokemon = self.caller.get_pokemon_by_id(pid)
        if not pokemon:
            self.caller.msg("No such Pokémon.")
            return

        if item and not self.caller.has_item(item):
            self.caller.msg(f"You do not have a {item}.")
            return

        from pokemon.evolution import attempt_evolution

        new_species = attempt_evolution(pokemon, item=item)
        if not new_species:
            self.caller.msg("It doesn't seem to be able to evolve right now.")
            return

        if item:
            self.caller.remove_item(item)
        pokemon.save()
        self.caller.msg(f"{pokemon.name} evolved into {new_species}!")


class CmdExpShare(Command):
    """Toggle the EXP Share effect for your party."""

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
    """Heal your Pokémon party at a Pokémon Center."""

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
    """Heal another player's Pokémon party."""

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
