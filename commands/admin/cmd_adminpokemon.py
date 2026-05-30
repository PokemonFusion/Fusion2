import uuid

from evennia import Command

from pokemon.models.core import OwnedPokemon
from pokemon.models.trainer import Trainer


class CmdListPokemon(Command):
	"""List a character's Pokémon.

	Usage:
	  @listpokemon <character>
	"""

	key = "@listpokemon"
	locks = "cmd:perm(Builder)"
	help_category = "Admin"

	def func(self):
		if not self.args:
			self.caller.msg("Usage: @listpokemon <character>")
			return
		target = self.caller.search(self.args.strip(), global_search=True)
		if not target:
			return
		storage = getattr(target, "storage", None)
		if not storage:
			self.caller.msg("Target has no Pokémon storage.")
			return
		party = storage.get_party()
		stored = storage.get_stored_pokemon()
		lines = [f"Pokémon for {target.key}:"]
		if party:
			lines.append(" Active party:")
			for idx, mon in enumerate(party, start=1):
				lines.append(f"  {mon.name} Lv{mon.computed_level} ID:{mon.unique_id}")
		else:
			lines.append(" No active Pokémon.")
		if stored:
			lines.append(" Stored Pokémon:")
			for mon in stored:
				lines.append(f"  {mon.name} Lv{mon.computed_level} ID:{mon.unique_id}")
		else:
			lines.append(" No stored Pokémon.")
		self.caller.msg("\n".join(lines))


class CmdRemovePokemon(Command):
	"""Delete a Pokémon by its ID.

	Usage:
	  @removepokemon <pokemon_id>
	"""

	key = "@removepokemon"
	locks = "cmd:perm(Wizards)"
	help_category = "Admin"

	def func(self):
		pid = self.args.strip()
		if not pid:
			self.caller.msg("Usage: @removepokemon <pokemon_id>")
			return
		pokemon = OwnedPokemon.objects.filter(unique_id=pid).first()
		if not pokemon:
			self.caller.msg("No Pokémon found with that ID.")
			return
		name = pokemon.name
		# Clear many-to-many relations to avoid orphaned slots
		pokemon.active_users.clear()
		pokemon.stored_users.clear()
		pokemon.boxes.clear()
		pokemon.delete()
		self.caller.msg(f"Removed {name} ({pid}).")


class CmdPokemonInfo(Command):
	"""Display detailed information about a Pokémon by GUID.

	Usage:
	  @pokemoninfo <pokemon_id>
	"""

	key = "@pokemoninfo"
	locks = "cmd:perm(Builder)"
	help_category = "Admin"

	def func(self):
		pid = self.args.strip()
		if not pid:
			self.caller.msg("Usage: @pokemoninfo <pokemon_id>")
			return
		try:
			uuid.UUID(pid)
		except Exception:
			self.caller.msg("|rInvalid GUID.|n")
			return
		pokemon = (
			OwnedPokemon.objects.select_related("active_moveset")
			.prefetch_related("learned_moves", "movesets__slots", "activemoveslot_set")
			.filter(unique_id=pid)
			.first()
		)
		if not pokemon:
			self.caller.msg("No Pokémon found with that ID.")
			return

		from django.forms.models import model_to_dict

		data = model_to_dict(
			pokemon,
			exclude=["learned_moves", "active_moveset"],
		)
		lines = [f"Data for {pokemon.name} ({pokemon.unique_id}):"]
		for key, val in data.items():
			if key == "trainer" and val:
				trainer = Trainer.objects.filter(pk=val).select_related("user").first()
				if trainer and hasattr(trainer, "user") and trainer.user:
					val = f"{val} ({trainer.user.key})"
			lines.append(f"  {key}: {val}")

		lines.append("Movesets:")
		for ms in pokemon.movesets.order_by("index"):
			moves = [s.move.name for s in ms.slots.order_by("slot")]
			marker = " (active)" if pokemon.active_moveset and ms.pk == pokemon.active_moveset.pk else ""
			move_str = ", ".join(moves) if moves else "(empty)"
			lines.append(f"  {ms.index + 1}: {move_str}{marker}")

		active_moves = [m.name for m in pokemon.active_moves]
		if active_moves:
			lines.append("Active moves: " + ", ".join(active_moves))
		else:
			lines.append("Active moves: (none)")
		self.caller.msg("\n".join(lines))


class CmdBackfillPokemonMovesets(Command):
	"""Backfill generated level-appropriate movesets.

	Usage:
	  @backfillmovesets
	  @backfillmovesets/apply [character|limit]
	  @backfillmovesets/replace [character|limit]
	"""

	key = "@backfillmovesets"
	locks = "cmd:perm(Wizards)"
	help_category = "Admin"

	def func(self):
		switches = {switch.lower() for switch in getattr(self, "switches", [])}
		dry_run = "apply" not in switches and "replace" not in switches
		replace_active = "replace" in switches
		args = (self.args or "").strip()

		queryset = OwnedPokemon.objects.all()
		limit = None
		target_label = "all owned Pokemon"
		if args:
			if args.isdigit():
				limit = int(args)
				target_label = f"first {limit} owned Pokemon"
			else:
				target = self.caller.search(args, global_search=True)
				if not target:
					return
				trainer = getattr(target, "trainer", None)
				if not trainer:
					self.caller.msg("Target has no trainer profile.")
					return
				queryset = queryset.filter(trainer=trainer)
				target_label = f"{target.key}'s Pokemon"

		from pokemon.services.move_management import backfill_owned_pokemon_movesets

		summary = backfill_owned_pokemon_movesets(
			queryset=queryset,
			dry_run=dry_run,
			replace_active=replace_active,
			limit=limit,
		)
		mode = "Dry run" if dry_run else "Backfill"
		lines = [
			f"{mode} for {target_label}:",
			f"  Checked: {summary['checked']}",
			f"  Would update: {summary['would_update']}",
			f"  Updated: {summary['updated']}",
			f"  Skipped: {summary['skipped']}",
		]
		if summary["errors"]:
			lines.append(f"  Errors: {len(summary['errors'])}")
			lines.extend(f"    {err}" for err in summary["errors"][:5])
		if dry_run:
			lines.append("Run @backfillmovesets/apply to fill missing data without replacing active moves.")
			lines.append("Run @backfillmovesets/replace to rebuild active movesets from generated defaults.")
		self.caller.msg("\n".join(lines))
