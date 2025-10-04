"""Turn management mixin for battle sessions.

This module contains a :class:`TurnManager` mixin that encapsulates the common
turn-handling functionality used by :class:`~pokemon.battle.battleinstance.BattleSession`.
Private helper methods break the logic into smaller units which keeps the public
APIs :meth:`prompt_next_turn` and :meth:`run_turn` readable and easier to
maintain.
"""

from __future__ import annotations

import traceback

from utils.safe_import import safe_import

from .compat import log_err, log_info, log_warn
from .interface import format_turn_banner, render_interfaces

try:  # pragma: no cover - interface may be stubbed in tests
	broadcast_interfaces = safe_import("pokemon.battle.interface").broadcast_interfaces  # type: ignore[attr-defined]
except (ModuleNotFoundError, AttributeError):  # pragma: no cover - fallback implementation

	def broadcast_interfaces(session, *, waiting_on=None):  # type: ignore[misc]
		iface_a, iface_b, iface_w = render_interfaces(
			session.captainA, session.captainB, session.state, waiting_on=waiting_on
		)
		for t in getattr(session, "teamA", []):
			session._msg_to(t, iface_a)
		for t in getattr(session, "teamB", []):
			session._msg_to(t, iface_b)
		for w in getattr(session, "observers", []):
			session._msg_to(w, iface_w)


class TurnManager:
	"""Mixin providing turn flow helpers for battle sessions."""

	# ------------------------------------------------------------------
	# Private helpers
	# ------------------------------------------------------------------
	def _turn_number(self, *, upcoming: bool = False) -> int:
		"""Return the current or upcoming turn number."""

		if not self.battle:
			return 1

		turn_count = getattr(self.battle, "turn_count", 0) or 0

		if upcoming:
			# The engine's ``turn_count`` already tracks the next turn to
			# execute once the battle has started.  Clamp to 1 for the
			# initial announcement in case the counter is still zero.
			return max(1, turn_count)

		# When ``upcoming`` is ``False`` we are announcing the end of the
		# current turn.  Because the engine increments ``turn_count`` at the
		# start of ``run_turn``, subtract one so the closing banner matches
		# the actions that just resolved.
		completed_turn = turn_count - 1
		return max(1, completed_turn)

	def _announce_turn_headline(self) -> None:
		"""Announce the headline marker for the upcoming turn."""

		if not (self.state and self.battle):
			return
		turn_no = self._turn_number(upcoming=True)
		self.notify(f"== Turn {turn_no} ==")

	def _notify_turn_banner(self, *, upcoming: bool = False) -> None:
		"""Send the current turn banner to listeners if a battle is active."""

		if not (self.state and self.battle):
			return
		turn_no = self._turn_number(upcoming=upcoming)
		self.notify(format_turn_banner(turn_no, closing=not upcoming))

	def _render_interfaces(self) -> None:
		"""Render and broadcast battle interfaces to participants and watchers."""

		if self.captainA and self.state and self.captainB is not None:
			try:
				broadcast_interfaces(self)
			except Exception:
				log_warn("Failed to display battle interface", exc_info=True)

	def _persist_turn_state(self) -> None:
		"""Persist the current turn's data and state to backing storage."""

		if getattr(self, "storage", None):
			try:
				self.storage.set("data", self.logic.data.to_dict())
				self.storage.set(
					"state",
					self._compact_state_for_persist(self.logic.state.to_dict()),
				)
			except Exception:
				log_warn("Failed to persist battle state", exc_info=True)

	# ------------------------------------------------------------------
	# Public API
	# ------------------------------------------------------------------
	def prompt_next_turn(self) -> None:
		"""Prompt the player to issue a command for the next turn."""

		self._set_player_control(True)
		self._announce_turn_headline()
		self._render_interfaces()
		prompt_hook = getattr(self, "_prompt_active_pokemon", None)
		if callable(prompt_hook):
			try:
				prompt_hook()
			except Exception:
				log_warn("Failed to prompt active Pokémon", exc_info=True)
		self.msg("The battle awaits your move.")
		if self.battle and getattr(self.battle, "turn_count", 0) == 1:
			log_info(f"Prompted first turn for battle {self.battle_id}")

	def run_turn(self) -> None:
		"""Advance the battle by one turn."""

		if not self.battle:
			return

		log_info(f"Running turn for battle {self.battle_id}")
		self._set_player_control(False)
		self._notify_turn_banner(upcoming=True)
		battle_finished = False
		try:
			self.battle.run_turn()
		except Exception:
			err_txt = traceback.format_exc()
			self.turn_state["error"] = err_txt
			log_err(
				f"Error while running turn for battle {self.battle_id}:\n{err_txt}",
				exc_info=False,
			)
			self.notify(f"Battle error:\n{err_txt}")
		else:
			battle = self.battle
			roster_size = 0
			winner = None
			if battle and getattr(battle, "participants", None):
				try:
					roster_size = sum(len(getattr(part, "pokemons", [])) for part in battle.participants)
				except Exception:
					roster_size = 0
			if battle:
				try:
					if hasattr(battle, "check_win_conditions"):
						winner = battle.check_win_conditions()
						battle_finished = getattr(battle, "battle_over", False) or bool(winner)
					else:
						battle_finished = getattr(battle, "battle_over", False)
				except Exception:
					log_warn("Failed to evaluate battle win conditions", exc_info=True)
					battle_finished = getattr(battle, "battle_over", False)
				if roster_size <= 0 and not winner:
					battle_finished = False
			log_info(f"Finished turn {getattr(self.battle, 'turn_count', '?')} for battle {self.battle_id}")
			if self.state:
				# Keep the battle state in sync with the engine's turn counter so
				# interfaces relying on ``state.turn`` reflect the current turn.
				self.state.turn = getattr(self.battle, "turn_count", self.state.turn)
			if self.data and getattr(self.data, "battle", None):
				self.data.battle.turn = getattr(self.battle, "turn_count", self.data.battle.turn)
			self._notify_turn_banner()
			if battle_finished:
				if hasattr(self, "end"):
					try:
						self.end()  # type: ignore[misc]
					except Exception:
						log_err(
							f"Failed to finalize battle {self.battle_id}",
							exc_info=True,
						)
					return

		if self.state:
			self.state.declare.clear()
		if self.data:
			for pos in self.data.turndata.positions.values():
				pos.removeDeclare()

		self._persist_turn_state()
		self.prompt_next_turn()


__all__ = ["TurnManager"]
