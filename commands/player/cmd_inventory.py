"""Inventory-related command set for Pokémon game.

This module houses commands dealing with a player's inventory, such as
viewing items, adding new ones, giving them to others and using them.
"""

from evennia import Command

from utils.dex_suggestions import item_not_found_message
from utils.locks import require_no_battle_lock


def _inventory_item_key(item_name: str) -> tuple[str | None, object | None, str]:
    """Return canonical dex key, data object, and stored inventory key."""

    from pokemon.middleware import get_item_by_name

    canonical, data = get_item_by_name(item_name)
    if canonical:
        return canonical, data, canonical.lower()
    fallback = (item_name or "").replace(" ", "").replace("-", "").replace("'", "").lower()
    return None, None, fallback


def _display_item_name(data, fallback: str) -> str:
    raw = getattr(data, "raw", None)
    display = raw.get("name") if isinstance(raw, dict) else None
    display = display or (data.get("name") if isinstance(data, dict) else None)
    display = display or getattr(data, "name", None)
    return display or str(fallback).title()


def _growth_rate_for_pokemon(pokemon) -> str:
    growth = getattr(pokemon, "growth_rate", None)
    if growth:
        return growth
    species_name = getattr(pokemon, "species", getattr(pokemon, "name", ""))
    if species_name:
        from pokemon.dex import POKEDEX

        entry = (
            POKEDEX.get(species_name)
            or POKEDEX.get(str(species_name).lower())
            or POKEDEX.get(str(species_name).capitalize())
        )
        if entry:
            return (getattr(entry, "raw", {}) or {}).get("growthRate", "medium_fast")
    return "medium_fast"


def _apply_rare_candy(caller, trainer, pokemon, item_key: str) -> None:
    level = getattr(pokemon, "computed_level", getattr(pokemon, "level", 1))
    if level >= 100:
        caller.msg(f"{pokemon.name} is already level 100.")
        return

    from pokemon.models.stats import add_experience, exp_for_level

    growth = _growth_rate_for_pokemon(pokemon)
    target_exp = exp_for_level(level + 1, growth)
    current_exp = int(getattr(pokemon, "total_exp", 0) or 0)
    gained = max(0, target_exp - current_exp)
    if not trainer.remove_item(item_key):
        caller.msg("You don't have any Rare Candy to use.")
        return

    if gained:
        add_experience(pokemon, gained, rate=growth, caller=caller)
    elif hasattr(pokemon, "set_level"):
        pokemon.set_level(level + 1)
    else:
        pokemon.level = level + 1
    if hasattr(pokemon, "save"):
        try:
            pokemon.save()
        except Exception:
            pass
    new_level = getattr(pokemon, "computed_level", getattr(pokemon, "level", level + 1))
    caller.msg(f"{pokemon.name} grew to level {new_level}.")


class CmdInventory(Command):
    """Show items in your inventory.

    Usage:
      +inventory

    Examples:
      +inventory

    Notes:
      Use +use for field-use items and +battle/item for battle items.
    """

    key = "+inventory"
    aliases = ["inventory"]
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
        from pokemon.middleware import get_item_by_name, get_item_description

        for entry in entries:
            item_name, data = get_item_by_name(entry.item_name)
            item_name = item_name or entry.item_name
            desc = get_item_description(item_name, data)
            display = _display_item_name(data, item_name)
            lines.append(f"{display} x{entry.quantity} - {desc}")
        self.caller.msg("\n".join(lines))


class CmdAddItem(Command):
    """Add an item to your inventory.

    Usage:
      @additem <item> <amount>
    """

    key = "@additem"
    aliases = ["additem"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        parts = self.args.split()
        if len(parts) != 2:
            self.caller.msg("Usage: @additem <item> <amount>")
            return
        item = parts[0]
        try:
            qty = int(parts[1])
        except ValueError:
            self.caller.msg("Usage: @additem <item> <amount>")
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
      @giveitem <player> = <item>:<amount>
    """

    key = "@giveitem"
    aliases = ["+giveitem"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def parse(self):
        self.amount_error = False
        parts = self.args.split("=")
        if len(parts) != 2:
            self.target_name = self.item_name = self.amount = None
            return
        self.target_name = parts[0].strip()
        item_part = parts[1].strip().split(":")
        self.item_name = item_part[0].strip().lower()
        try:
            self.amount = int(item_part[1].strip()) if len(item_part) > 1 else 1
        except ValueError:
            self.amount = None
            self.amount_error = True

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        if not all([self.target_name, self.item_name]):
            self.caller.msg("Usage: @giveitem <player> = <item>:<amount>")
            return
        if self.amount_error:
            self.caller.msg("Amount must be a number.")
            return

        target = self.caller.search(self.target_name)
        if not target or not hasattr(target, "trainer"):
            self.caller.msg("Player not found or has no trainer record.")
            return
        if not require_no_battle_lock(target):
            return

        canonical, _data, item_key = _inventory_item_key(self.item_name)
        if not canonical:
            self.caller.msg(
                item_not_found_message(
                    self.item_name,
                    f"Item '{self.item_name}' not found in ITEMDEX.",
                )
            )
            return

        target.trainer.add_item(item_key, self.amount)
        self.caller.msg(f"Gave {self.amount} x {canonical} to {target.key}.")


class CmdUseItem(Command):
    """Use an item outside of battle.

    Usage:
      +use <item>
      +use <slot>=<item>

    Examples:
      +use Potion
      +use 2=PP Up

    Notes:
      Battle items use +battle/item while a battle is waiting for your action.
    """

    key = "+use"
    aliases = ["+useitem"]
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
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
            self.caller.msg("Usage: +use <item> or +use <slot>=<item>")
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

        canonical, item_data, item_name = _inventory_item_key(item_name)

        if not canonical:
            self.caller.msg(item_not_found_message(item_name, f"No such item '{item_name}' exists."))
            return

        if slot is not None and item_name in {"ppup", "ppmax"}:
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
            lines.append("Use +use <move name or number> to select.")
            self.caller.msg("\n".join(lines))
            return

        if item_name == "rarecandy":
            if slot is None:
                self.caller.msg("Usage: +use <slot>=Rare Candy")
                return
            pokemon = self.caller.get_active_pokemon_by_slot(slot)
            if not pokemon:
                self.caller.msg("No Pokemon in that slot.")
                return
            _apply_rare_candy(self.caller, trainer, pokemon, item_name)
            return

        success = trainer.remove_item(item_name)
        if not success:
            self.caller.msg(f"You don't have any {_display_item_name(item_data, canonical)} to use.")
            return

        # Placeholder for other item effects
        self.caller.msg(f"You used one {_display_item_name(item_data, canonical)}.")
