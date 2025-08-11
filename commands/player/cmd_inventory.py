"""Inventory-related command set for Pokémon game.

This module houses commands dealing with a player's inventory, such as
viewing items, adding new ones, giving them to others and using them.
"""

from evennia import Command

from pokemon.dex import ITEMDEX


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

