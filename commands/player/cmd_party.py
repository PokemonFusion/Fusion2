"""Party management commands for the Pokémon game.

This module groups commands that interact with a player's Pokémon party
and storage boxes.
"""

from evennia import Command

from utils.locks import require_no_battle_lock


class CmdDepositPokemon(Command):
    """Deposit a party Pokemon into a storage box.

    Usage:
      +box/deposit <pokemon_id> [box]

    Examples:
      +box/deposit abc123
      +box/deposit abc123 2

    Notes:
      You cannot change party storage while you are in battle.
    """

    key = "+box/deposit"
    aliases = ["deposit", "+deposit"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        parts = self.args.split()
        if not parts:
            self.caller.msg("Usage: +box/deposit <pokemon_id> [box]")
            return
        pid = parts[0]
        try:
            box = int(parts[1]) if len(parts) > 1 else 1
        except ValueError:
            self.caller.msg("Usage: +box/deposit <pokemon_id> [box]")
            return
        self.caller.msg(self.caller.deposit_pokemon(pid, box))


class CmdWithdrawPokemon(Command):
    """Withdraw a boxed Pokemon into your active party.

    Usage:
      +box/withdraw <pokemon_id> [box]

    Examples:
      +box/withdraw abc123
      +box/withdraw abc123 2

    Notes:
      If your party is full, use +box/swap instead.
    """

    key = "+box/withdraw"
    aliases = ["withdraw", "+withdraw"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        parts = self.args.split()
        if not parts:
            self.caller.msg("Usage: +box/withdraw <pokemon_id> [box]")
            return
        pid = parts[0]
        try:
            box = int(parts[1]) if len(parts) > 1 else 1
        except ValueError:
            self.caller.msg("Usage: +box/withdraw <pokemon_id> [box]")
            return
        self.caller.msg(self.caller.withdraw_pokemon(pid, box))


class CmdSwapPokemon(Command):
    """Swap a boxed Pokemon with one in your active party.

    Usage:
      +box/swap <pokemon_id> <party_slot> [box]

    Examples:
      +box/swap abc123 3
      +box/swap abc123 3 2

    Notes:
      Party slots run from 1 to 6.
    """

    key = "+box/swap"
    aliases = ["swap", "+swap", "pokemonswap", "boxswap"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        parts = self.args.split()
        if len(parts) < 2:
            self.caller.msg("Usage: +box/swap <pokemon_id> <party_slot> [box]")
            return
        pid = parts[0]
        try:
            slot = int(parts[1])
            box = int(parts[2]) if len(parts) > 2 else 1
        except ValueError:
            self.caller.msg("Usage: +box/swap <pokemon_id> <party_slot> [box]")
            return
        self.caller.msg(self.caller.swap_pokemon(pid, slot, box))


class CmdShowBox(Command):
    """Show the contents of a storage box.

    Usage:
      +box [box_number]

    Examples:
      +box
      +box 2

    Notes:
      Use +storage at a Pokemon Center for the interactive storage menu.
    """

    key = "+box"
    aliases = ["showbox", "+showbox"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        try:
            index = int(self.args.strip() or "1")
        except ValueError:
            self.caller.msg("Usage: +box [box_number]")
            return
        self.caller.msg(self.caller.show_box(index))


class CmdSetHoldItem(Command):
    """Give one of your active Pokemon a held item.

    Usage:
      +hold <slot>=<item>

    Examples:
      +hold 1=Oran Berry

    Notes:
      The item must be carried by your character.
    """

    key = "+hold"
    aliases = ["setholditem", "+setholditem"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: +hold <slot>=<item>")
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
    """Show chargen details and active Pokemon.

    Usage:
      chargeninfo

    Examples:
      chargeninfo

    Notes:
      This is mostly useful while finishing character setup.
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
            mons = storage.get_party()
            if mons:
                lines.append("  Active Pokémon:")
                for mon in mons:
                    lines.append(f"    {mon.name} (Lv {mon.computed_level}, Ability: {mon.ability})")
            else:
                lines.append("  Active Pokémon: None")
        else:
            lines.append("  No storage data.")
        char.msg("\n".join(lines))
