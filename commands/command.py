from evennia import Command
from pokemon.generation import generate_pokemon
from pokemon.stats import calculate_stats

from pokemon.dex import ITEMDEX

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
    """Search for a wild Pokémon or a trainer to battle.

    Usage:
      +hunt
    """

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


class CmdDepositPokemon(Command):
    """Deposit a Pokémon into a storage box.

    Usage:
      deposit <pokemon_id> [box]
    """

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
    """Withdraw a Pokémon from a storage box.

    Usage:
      withdraw <pokemon_id> [box]
    """

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
    """Show the contents of a storage box.

    Usage:
      showbox <box_number>
    """

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
    """Give one of your active Pokémon a held item.

    Usage:
      setholditem <slot>=<item>
    """

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
    """Show chargen details and active Pokémon.

    Usage:
      chargeninfo
    """

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
            mons = storage.get_party() if hasattr(storage, "get_party") else list(storage.active_pokemon.all())
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
    """Show items in your inventory.

    Usage:
      +inventory
    """

    key = "+inventory"
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        trainer = getattr(self.caller, "trainer", None)
        if not trainer:
            self.caller.msg("You have no trainer record.")
            return

        entries = trainer.list_inventory()
        if not entries:
            self.caller.msg("Your inventory is empty.")
            return

        lines = ["Your Inventory:"]
        for entry in entries:
            data = ITEMDEX.get(entry.item_name, {})
            desc = data.get("desc", "No description available.")
            lines.append(f"{entry.item_name.title()} x{entry.quantity} - {desc}")
        self.caller.msg("\n".join(lines))


class CmdAddItem(Command):
    """Add an item to your inventory.

    Usage:
      additem <item> <amount>
    """

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
        trainer = getattr(self.caller, "trainer", None)
        if not trainer:
            self.caller.msg("You have no trainer record.")
            return
        trainer.add_item(item, qty)
        self.caller.msg(f"Added {qty} x {item}.")


class CmdGiveItem(Command):
    """Give an item to another player (admin-only).

    Usage:
      +giveitem <player> = <item>:<amount>
    """

    key = "+giveitem"
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def parse(self):
        parts = self.args.split("=")
        if len(parts) != 2:
            self.target_name = self.item_name = self.amount = None
            return
        self.target_name = parts[0].strip()
        item_part = parts[1].strip().split(":")
        self.item_name = item_part[0].strip().lower()
        self.amount = int(item_part[1].strip()) if len(item_part) > 1 else 1

    def func(self):
        if not all([self.target_name, self.item_name]):
            self.caller.msg("Usage: +giveitem <player> = <item>:<amount>")
            return

        target = self.caller.search(self.target_name)
        if not target or not hasattr(target, "trainer"):
            self.caller.msg("Player not found or has no trainer record.")
            return

        if self.item_name not in ITEMDEX:
            self.caller.msg(f"Item '{self.item_name}' not found in ITEMDEX.")
            return

        target.trainer.add_item(self.item_name, self.amount)
        self.caller.msg(f"Gave {self.amount} x {self.item_name} to {target.key}.")


class CmdUseItem(Command):
    """Use an item outside of battle.

    Usage:
      +useitem <item>
      +useitem <slot>=<item>
    """

    key = "+useitem"
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        args = self.args.strip()
        trainer = getattr(self.caller, "trainer", None)

        if not trainer:
            self.caller.msg("You have no trainer record.")
            return

        pending = getattr(self.caller.ndb, "pending_pp_item", None)

        if pending:
            move_sel = args.strip()
            if not move_sel:
                self.caller.msg("Please specify which move to apply the item to.")
                return
            pokemon = pending["pokemon"]
            item = pending["item"]
            slots = list(pokemon.activemoveslot_set.order_by("slot"))
            move_name = None
            if move_sel.isdigit():
                idx = int(move_sel) - 1
                if 0 <= idx < len(slots):
                    move_name = slots[idx].move.name
            else:
                for s in slots:
                    if s.move.name.lower() == move_sel.lower():
                        move_name = s.move.name
                        break
            if not move_name:
                self.caller.msg("Invalid move selection.")
                return
            if item == "ppup":
                applied = pokemon.apply_pp_up(move_name)
                fail_msg = "That move's PP can't be raised any further."
            else:
                applied = pokemon.apply_pp_max(move_name)
                fail_msg = "That move already has maximum PP."
            if not applied:
                self.caller.msg(fail_msg)
                self.caller.ndb.pending_pp_item = None
                return
            trainer.remove_item(item)
            self.caller.msg(f"{pokemon.name}'s {move_name} PP was increased.")
            self.caller.ndb.pending_pp_item = None
            return

        if not args:
            self.caller.msg("Usage: +useitem <item> or +useitem <slot>=<item>")
            return

        slot = None
        item_name = args
        if "=" in args:
            left, right = [p.strip() for p in args.split("=", 1)]
            try:
                slot = int(left)
            except ValueError:
                self.caller.msg("Invalid slot number.")
                return
            item_name = right

        item_name = item_name.lower()

        if item_name not in ITEMDEX:
            self.caller.msg(f"No such item '{item_name}' exists.")
            return

        if slot is not None and item_name in {"ppup", "ppmax", "pp max"}:
            pokemon = self.caller.get_active_pokemon_by_slot(slot)
            if not pokemon:
                self.caller.msg("No Pokémon in that slot.")
                return
            slots = list(pokemon.activemoveslot_set.order_by("slot"))
            if not slots:
                self.caller.msg("That Pokémon knows no moves.")
                return
            self.caller.ndb.pending_pp_item = {"pokemon": pokemon, "item": item_name.replace(" ", "")}
            lines = ["Choose a move to increase PP:"]
            for s in slots:
                max_pp = pokemon.get_max_pp(s.move.name)
                lines.append(f"{s.slot}. {s.move.name.title()} ({s.current_pp}/{max_pp})")
            lines.append("Use +useitem <move name or number> to select.")
            self.caller.msg("\n".join(lines))
            return

        success = trainer.remove_item(item_name)
        if not success:
            self.caller.msg(f"You don't have any {item_name} to use.")
            return

        # Placeholder for other item effects
        self.caller.msg(f"You used one {item_name}.")


class CmdEvolvePokemon(Command):
    """Evolve one of your Pokémon if possible.

    Usage:
      evolve <pokemon_id> [item]
    """

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
            self.caller.trainer.remove_item(item)
        pokemon.save()
        self.caller.msg(f"{pokemon.name} evolved into {new_species}!")


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


class CmdChooseMoveset(Command):
    """Select which stored moveset a Pokémon should use.

    Usage:
      +moveset <slot>=<set#>
    """

    key = "+moveset"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        if "=" not in self.args:
            self.slot = self.index = None
            return
        left, right = [p.strip() for p in self.args.split("=", 1)]
        try:
            self.slot = int(left)
            self.index = int(right) - 1
        except ValueError:
            self.slot = self.index = None

    def func(self):
        if self.slot is None or self.index is None:
            self.caller.msg("Usage: +moveset <slot>=<set#>")
            return
        pokemon = self.caller.get_active_pokemon_by_slot(self.slot)
        if not pokemon:
            self.caller.msg("No Pokémon in that slot.")
            return
        sets = pokemon.movesets or []
        if self.index < 0 or self.index >= len(sets):
            self.caller.msg("Invalid moveset number.")
            return
        pokemon.swap_moveset(self.index)
        self.caller.msg(f"{pokemon.name} is now using moveset {self.index + 1}.")


class CmdTeachMove(Command):
    """Teach a move to one of your active Pokémon.

    Usage:
      +move <slot>=<move>
    """

    key = "+move"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        if "=" not in self.args:
            self.slot = None
            self.move_name = ""
            return
        left, right = [p.strip() for p in self.args.split("=", 1)]
        try:
            self.slot = int(left)
        except ValueError:
            self.slot = None
        self.move_name = right.strip()

    def func(self):
        if self.slot is None or not self.move_name:
            self.caller.msg("Usage: +move <slot>=<move>")
            return
        pokemon = self.caller.get_active_pokemon_by_slot(self.slot)
        if not pokemon:
            self.caller.msg("No Pokémon in that slot.")
            return
        from pokemon.generation import get_valid_moves
        from pokemon.models import Move

        valid = [m.lower() for m in get_valid_moves(pokemon.species, pokemon.level)]
        if self.move_name.lower() not in valid:
            self.caller.msg(f"{pokemon.name} cannot learn {self.move_name}.")
            return
        if pokemon.learned_moves.filter(name__iexact=self.move_name).exists():
            self.caller.msg(f"{pokemon.name} already knows {self.move_name}.")
            return

        from pokemon.utils.move_learning import learn_move

        learn_move(pokemon, self.move_name, caller=self.caller, prompt=True)

class CmdLearn(Command):
    """Learn level-up moves for a Pokémon.

    Usage:
      +learn <slot>
    """

    key = "+learn"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        try:
            self.slot = int(self.args.strip())
        except (TypeError, ValueError):
            self.slot = None

    def func(self):
        from pokemon.utils.move_learning import get_learnable_levelup_moves

        if self.slot is None:
            lines = []
            for idx in range(1, 7):
                poke = self.caller.get_active_pokemon_by_slot(idx)
                if not poke:
                    continue
                moves, _ = get_learnable_levelup_moves(poke)
                if moves:
                    lines.append(
                        f"Slot {idx}: {poke.name} ({len(moves)} move{'s' if len(moves) != 1 else ''})"
                    )
            if lines:
                self.caller.msg("Pokémon with moves to learn:\n" + "\n".join(lines))
            else:
                self.caller.msg("None of your Pokémon have moves to learn.")
            return

        pokemon = self.caller.get_active_pokemon_by_slot(self.slot)
        if not pokemon:
            self.caller.msg("No Pokémon in that slot.")
            return

        moves, level_map = get_learnable_levelup_moves(pokemon)
        if not moves:
            self.caller.msg(f"{pokemon.name} has no moves to learn.")
            return

        from pokemon.utils.enhanced_evmenu import EnhancedEvMenu
        from menus import learn_new_moves as learn_menu

        EnhancedEvMenu(
            self.caller,
            learn_menu,
            startnode="node_start",
            kwargs={"pokemon": pokemon, "moves": moves, "level_map": level_map},
            cmd_on_exit=None,
        )
