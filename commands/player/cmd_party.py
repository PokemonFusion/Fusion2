"""Party management commands for the Pokémon game.

This module groups commands that interact with a player's Pokémon party
and storage boxes.
"""

from evennia import Command

from utils.locks import require_no_battle_lock


class CmdDepositPokemon(Command):
	"""Deposit a Pokémon into a storage box.

	Usage:
	  deposit <pokemon_id> [box]
	"""

	key = "deposit"
	locks = "cmd:all()"
	help_category = "Pokemon"

	def func(self):
		if not require_no_battle_lock(self.caller):
			return
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
		if not require_no_battle_lock(self.caller):
			return
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
		if not require_no_battle_lock(self.caller):
			return
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
					lines.append(f"    {mon.name} (Lv {mon.computed_level}, Ability: {mon.ability})")
			else:
				lines.append("  Active Pokémon: None")
		else:
			lines.append("  No storage data.")
		char.msg("\n".join(lines))
