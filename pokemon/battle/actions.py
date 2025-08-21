"""Battle action models and lifecycle helpers.

This module defines the :class:`Action` container and helpers managing the
battle lifecycle. Content was extracted from ``engine.py`` for clarity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pokemon.battle.participants import BattleParticipant


class ActionType(Enum):
	"""Enumeration of possible battle actions."""

	MOVE = 1
	SWITCH = 2
	ITEM = 3
	RUN = 4


@dataclass
class Action:
	"""Container describing a chosen action for the turn."""

	actor: BattleParticipant
	action_type: ActionType
	target: Optional[BattleParticipant] = None
	move: Optional[Any] = None
	item: Optional[str] = None
	priority: int = 0
	priority_mod: float = 0.0
	speed: int = 0
	pokemon: Optional[Any] = None


class BattleActions:
	"""Mixin implementing battle lifecycle helpers."""

	def check_victory(self) -> Optional[BattleParticipant]:
		remaining = [p for p in self.participants if not p.has_lost]
		if len(remaining) <= 1:
			self.battle_over = True
			self.restore_transforms()
			return remaining[0] if remaining else None
		return None

	def perform_switch_action(self, participant: BattleParticipant, new_pokemon) -> None:
		"""Execute a switch action for ``participant``."""
		if participant not in self.participants:
			return
		self.switch_pokemon(participant, new_pokemon)
		self.check_victory()

	def check_win_conditions(self) -> Optional[BattleParticipant]:
		"""Check and return the winning participant if battle has ended."""
		winner = self.check_victory()
		if winner:
			self.handle_end_of_battle_rewards(winner)
		return winner

	def handle_end_of_battle_rewards(self, winner: BattleParticipant) -> None:
		"""Placeholder for reward handling after battle ends."""
		pass


__all__ = ["ActionType", "Action", "BattleActions"]
