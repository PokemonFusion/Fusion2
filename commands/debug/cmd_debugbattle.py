"""Command to toggle battle debug output."""

from __future__ import annotations

from evennia import Command, search_object


class CmdDebugBattle(Command):
	"""Toggle debug output for an active battle.

	Usage:
	  +debug/battle <character or battle id>
	"""

	key = "+debug/battle"
	locks = "cmd:perm(Builder)"
	help_category = "Pokemon"

	def func(self):  # type: ignore[override]
		if not self.args:
			self.caller.msg("Usage: +debug/battle <character or battle id>")
			return
		arg = self.args.strip()
		inst = None
		if arg.isdigit():
			from pokemon.battle.handler import battle_handler

			inst = battle_handler.instances.get(int(arg))
		else:
			targets = search_object(arg)
			if targets:
				target = targets[0]
				inst = getattr(target.ndb, "battle_instance", None)
		if not inst or not getattr(inst, "state", None):
			self.caller.msg("No active battle found.")
			return
		state = inst.state
		state.debug = not getattr(state, "debug", False)
		if inst.battle:
			inst.battle.debug = state.debug
			inst.battle.fail_fast_errors = state.debug
		try:
			compact = getattr(inst, "_compact_state_for_persist", None)
			payload = compact(state.to_dict()) if callable(compact) else state.to_dict()
			inst.storage.set("state", payload)
		except Exception:
			pass
		status = "enabled" if state.debug else "disabled"
		debug_hook = getattr(inst, "persist_debug_record", None)
		if callable(debug_hook):
			try:
				debug_hook(event="debug_toggled", enabled=state.debug)
			except Exception:
				pass
		inst.notify(f"[DEBUG] Battle debug {status} by {getattr(self.caller, 'key', self.caller)}.")
		self.caller.msg(f"Battle debug {status}.")
