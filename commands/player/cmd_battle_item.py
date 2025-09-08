"""Command for using an item during battle."""

from __future__ import annotations

from evennia import Command

from world.system_init import get_system

from .cmd_battle_utils import NOT_IN_BATTLE_MSG, _get_participant

try:  # pragma: no cover - battle engine may not be available in tests
	from pokemon.battle import Action, ActionType

	if Action is None or ActionType is None:  # type: ignore[truthy-bool]
		raise ImportError
except Exception:  # pragma: no cover - fallback if engine isn't loaded
	from pokemon.battle.engine import Action, ActionType


class CmdBattleItem(Command):
	"""Use an item during battle.

	Usage:
	  +battle/item <item>
	"""

	key = "+battle/item"
	aliases = ["+item", "+Item", "+battleitem"]
	locks = "cmd:all()"
	help_category = "Pokemon/Battle"

	def func(self):
		if not getattr(self.caller.db, "battle_control", False):
			self.caller.msg("|rWe aren't waiting for you to command right now.")
			return
		item_name = self.args.strip()
		if not item_name:
			self.caller.msg("Usage: +battle/item <item>")
			return
		if not self.caller.has_item(item_name):
			self.caller.msg(f"You do not have any {item_name}.")
			return
		system = get_system()
		manager = getattr(system, "battle_manager", None)
		inst = manager.for_player(self.caller) if manager else None
		if not inst:
			try:  # pragma: no cover - battle session may be absent in tests
				from pokemon.battle.battleinstance import BattleSession
			except Exception:  # pragma: no cover

				class BattleSession:  # type: ignore[override]
					@staticmethod
					def ensure_for_player(caller):
						return getattr(caller.ndb, "battle_instance", None)

			inst = BattleSession.ensure_for_player(self.caller)
		if not inst or not getattr(inst, "battle", None):
			self.caller.msg(NOT_IN_BATTLE_MSG)
			return
		participant = _get_participant(inst, self.caller)
		target = inst.battle.opponent_of(participant)
		action = Action(
			participant,
			ActionType.ITEM,
			target,
			item=item_name,
			priority=6,
		)
		participant.pending_action = action
		if hasattr(self.caller, "trainer"):
			self.caller.trainer.remove_item(item_name)
		self.caller.msg(f"You prepare to use {item_name}.")
		if hasattr(inst, "queue_item"):
			try:
				inst.queue_item(item_name, caller=self.caller)
			except Exception:
				pass
		elif hasattr(inst, "maybe_run_turn"):
			try:
				inst.maybe_run_turn()
			except Exception:
				pass
