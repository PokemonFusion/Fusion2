"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

import importlib.machinery
import importlib.util
import os
import sys

from evennia.objects.objects import DefaultCharacter

_BASE_PATH = os.path.dirname(__file__)
if "typeclasses" not in sys.modules:
        spec_pkg = importlib.machinery.ModuleSpec("typeclasses", loader=None, is_package=True)
        pkg = importlib.util.module_from_spec(spec_pkg)
        pkg.__path__ = [_BASE_PATH]
        sys.modules["typeclasses"] = pkg

try:
	from .objects import ObjectParent
except Exception:  # pragma: no cover - fallback when package missing
	spec_obj = importlib.util.spec_from_file_location("typeclasses.objects", os.path.join(_BASE_PATH, "objects.py"))
	mod_obj = importlib.util.module_from_spec(spec_obj)
	sys.modules[spec_obj.name] = mod_obj
	spec_obj.loader.exec_module(mod_obj)
	ObjectParent = mod_obj.ObjectParent  # type: ignore[attr-defined]

from django.utils.translation import gettext as _

from pokemon.battle.interface import format_turn_banner
from utils.locks import require_no_battle_lock
from utils.pokedex import DexTrackerMixin


class Character(DexTrackerMixin, ObjectParent, DefaultCharacter):
	"""Default in-game character."""

	def at_init(self):
		super().at_init()
		self._restore_battle_instance()

	def _restore_battle_instance(self):
		"""Attach the active battle session to this character if one exists."""

		ndb = getattr(self, "ndb", None)
		if ndb and getattr(ndb, "battle_instance", None):
			return ndb.battle_instance

		try:
			from pokemon.battle.battleinstance import BattleSession
		except Exception:
			return None

		try:
			return BattleSession.ensure_for_player(self)
		except Exception:
			return None

	def _battle_waiting_on(self, inst):
		"""Return the first non-AI Pokemon still needing an action."""

		data = getattr(inst, "data", None)
		if not data:
			return None
		positions = getattr(getattr(data, "turndata", None), "positions", {}) or {}
		state = getattr(inst, "state", None)
		declared = getattr(state, "declare", {}) or {}
		battle = getattr(inst, "battle", None)

		for pos_name, pos in positions.items():
			has_action = False
			try:
				has_action = bool(pos.getAction())
			except Exception:
				has_action = False
			if has_action or pos_name in declared:
				continue
			pokemon = getattr(pos, "pokemon", None)
			if not pokemon:
				continue
			participant = None
			if battle and hasattr(battle, "participant_for"):
				try:
					participant = battle.participant_for(pokemon)
				except Exception:
					participant = None
			if participant is not None and getattr(participant, "is_ai", False):
				continue
			return pokemon
		return None

	def _send_battle_recap(self, inst) -> None:
		"""Send a login recap for the battle this character is in."""

		if not getattr(inst, "state", None) or not getattr(inst, "captainA", None):
			return

		waiting_on = self._battle_waiting_on(inst)
		try:
			self.msg("|wYou are still in battle.|n")
		except Exception:
			pass

		try:
			from pokemon.battle.interface import send_interface_to

			send_interface_to(inst, self, waiting_on=waiting_on)
		except Exception:
			try:
				from pokemon.battle.interface import display_battle_interface

				viewer_team = None
				if self in getattr(inst, "teamA", []):
					viewer_team = "A"
				elif self in getattr(inst, "teamB", []):
					viewer_team = "B"
				ui = display_battle_interface(
					inst.captainA,
					inst.captainB,
					inst.state,
					viewer_team=viewer_team,
					waiting_on=waiting_on,
				)
				self.msg(ui)
			except Exception:
				pass

	def at_post_puppet(self):
		super().at_post_puppet()
		inst = self._restore_battle_instance()
		if inst:
			self._send_battle_recap(inst)

			if self in getattr(inst, "trainers", []):
				battle = getattr(inst, "battle", None)
				state = getattr(inst, "state", None)
				if battle or state:
					turn = getattr(battle, "turn_count", None) if battle else None
					if turn is None and state is not None:
						turn = getattr(state, "turn", None)
					if turn is None:
						turn = 1
					try:
						turn_no = int(turn)
					except Exception:
						turn_no = 1
					if turn_no < 1:
						turn_no = 1
					try:
						self.msg(format_turn_banner(turn_no))
					except Exception:
						pass
		try:
			from pokemon.adventures.cmdsets import attach_movement_cmdset
			from pokemon.adventures.sessions import sync_player_to_active_session

			if sync_player_to_active_session(self):
				attach_movement_cmdset(self)
		except Exception:
			pass

	def at_pre_move(self, destination, **kwargs):
		"""Prevent leaving while hosting a PVP request or during battles."""
		db = getattr(self, "db", None)
		if db is not None and getattr(db, "pvp_locked", False):
			self.msg("|rYou can't leave while waiting for a PVP battle.|n")
			return False

		if not require_no_battle_lock(self):
			return False

		return super().at_pre_move(destination, **kwargs)

	def at_say(
		self,
		message,
		msg_self=None,
		msg_location=None,
		receivers=None,
		msg_receivers=None,
		**kwargs,
	):
		"""Echo speech using the character's name to themselves.

		By default Evennia shows "You say" to the speaker while others see
		"<name> says".  This override aligns the speaker's view with everyone
		else's so that the player's name is shown in their own say messages as
		well.

		Args:
			message (str): The text to say.
			msg_self (str or bool, optional): Custom self message or a truthy
			value to use the default name-based format.
			msg_location (str, optional): Message for the location.
			receivers (DefaultObject or iterable, optional): Whom to whisper to.
			msg_receivers (str, optional): Message for specific receivers.
			**kwargs: Passed on to the parent implementation.
		"""

		if (msg_self is None or msg_self is True) and not kwargs.get("whisper", False):
			msg_self = _('{object} says, "|n{speech}|n"')

		return super().at_say(
			message,
			msg_self=msg_self,
			msg_location=msg_location,
			receivers=receivers,
			msg_receivers=msg_receivers,
			**kwargs,
		)
