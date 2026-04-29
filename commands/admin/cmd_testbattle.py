"""Staff-facing helpers for spawning and running debug battles."""

from __future__ import annotations

from evennia import Command

from pokemon.battle.battleinstance import BattleSession
from utils.dex_suggestions import (
	is_known_species,
	is_species_not_found_error,
	species_not_found_message,
)


def _parse_spawn_spec(spec: str) -> dict:
	"""Parse ``species[, level][, wild|trainer]`` into a dict."""

	parts = [part.strip() for part in (spec or "").split(",") if part.strip()]
	if not parts:
		raise ValueError("Usage: @testspawn <species>[, level][, wild|trainer]")
	species = parts[0]
	level = 5
	kind = "wild"
	for part in parts[1:]:
		if part.isdigit():
			level = max(1, int(part))
		elif part.lower() in {"wild", "trainer"}:
			kind = part.lower()
	return {"species": species, "level": level, "kind": kind}


class CmdTestSpawn(Command):
	"""Store or clear the current room's debug opponent configuration.

	Usage:
	  @testspawn <species>[, level][, wild|trainer]
	  @testspawn/clear
	"""

	key = "@testspawn"
	aliases = ["+testspawn"]
	locks = "cmd:perm(Builder)"
	help_category = "Admin"

	def parse(self):
		super().parse()
		self.switches = {switch.lower() for switch in getattr(self, "switches", [])}

	def func(self):
		room = getattr(self.caller, "location", None)
		if room is None:
			self.caller.msg("You must be in a room to configure a test spawn.")
			return
		if "clear" in self.switches:
			if hasattr(room.db, "test_battle_spawn"):
				delattr(room.db, "test_battle_spawn")
			self.caller.msg("Cleared the room's test battle spawn.")
			return
		try:
			payload = _parse_spawn_spec(self.args)
		except ValueError as err:
			self.caller.msg(str(err))
			return
		if not is_known_species(payload["species"]):
			self.caller.msg(species_not_found_message(payload["species"]))
			return
		room.db.test_battle_spawn = payload
		self.caller.msg(
			f"Stored test spawn: {payload['species']} Lv{payload['level']} ({payload['kind']})."
		)


class CmdStartTestBattle(Command):
	"""Start a generated debug battle for a character.

	Usage:
	  @testbattle/start <character>
	  @testbattle/start <character>=<species>[, level][, wild|trainer]
	"""

	key = "@testbattle/start"
	aliases = ["+testbattle/start", "@starttestbattle", "+starttestbattle"]
	locks = "cmd:perm(Builder)"
	help_category = "Admin"

	def func(self):
		if not self.args:
			self.caller.msg(
				"Usage: @testbattle/start <character>[=<species>[, level][, wild|trainer]]"
			)
			return

		target_expr = self.args
		spec = ""
		if "=" in self.args:
			target_expr, spec = [part.strip() for part in self.args.split("=", 1)]

		target = self.caller.search(target_expr.strip(), global_search=True)
		if not target:
			return
		if getattr(getattr(target, "ndb", None), "battle_instance", None):
			self.caller.msg("That character is already in a battle.")
			return

		if spec:
			try:
				payload = _parse_spawn_spec(spec)
			except ValueError as err:
				self.caller.msg(str(err))
				return
		else:
			payload = getattr(getattr(target, "location", None), "db", None)
			payload = getattr(payload, "test_battle_spawn", None)
			if not payload:
				self.caller.msg(
					"No room test spawn configured. Use @testspawn or provide an explicit species."
				)
				return
		if not is_known_species(payload["species"]):
			self.caller.msg(species_not_found_message(payload["species"]))
			return

		session = BattleSession(target)
		try:
			session.start_test_battle(
				species=payload["species"],
				level=int(payload.get("level", 5)),
				opponent_kind=str(payload.get("kind", "wild")),
			)
		except ValueError as err:
			if is_species_not_found_error(err):
				self.caller.msg(species_not_found_message(payload["species"]))
				return
			raise
		self.caller.msg(
			f"Started debug battle #{session.battle_id} for {target.key} against "
			f"{payload['species']} Lv{payload.get('level', 5)} ({payload.get('kind', 'wild')})."
		)


__all__ = ["CmdTestSpawn", "CmdStartTestBattle"]
