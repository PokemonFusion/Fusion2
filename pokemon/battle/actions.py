"""Battle action models and lifecycle helpers.

This module defines the :class:`Action` container and helpers managing the
battle lifecycle. Content was extracted from ``engine.py`` for clarity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Sequence

from pokemon.battle.participants import BattleParticipant


def _get_default_text() -> dict[str, dict[str, str]]:
	"""Return the default battle text mapping with a safe fallback."""

	try:  # pragma: no cover - optional dependency in lightweight tests
		from pokemon.data.text import DEFAULT_TEXT  # type: ignore
	except Exception:  # pragma: no cover - fallback when data package missing
		return {"default": {}}
	return DEFAULT_TEXT  # type: ignore[return-value]


def _format_result_message(key: str, names: Sequence[str]) -> str | None:
	"""Format a result message for ``key`` inserting ``names`` sequentially."""

	default_messages = _get_default_text().get("default", {})
	template = default_messages.get(key)
	if not template:
		return None
	values = [str(name) for name in names if name]
	if not values:
		return template
	message = template
	for value in values[:-1]:
		message = message.replace("[TRAINER]", value, 1)
	message = message.replace("[TRAINER]", values[-1])
	return message


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
			winner = remaining[0] if remaining else None
			if not getattr(self, "_result_logged", False) and hasattr(self, "log_action"):
				message: str | None = None
				if winner:
					if hasattr(self, "_format_default_message"):
						message = self._format_default_message(
							"winBattle",
							{"[TRAINER]": getattr(winner, "name", "Trainer")},
						)
					else:
						message = _format_result_message(
							"winBattle",
							[getattr(winner, "name", "Trainer")],
						)
				else:
					participants = getattr(self, "participants", [])
					names = [getattr(part, "name", "Trainer") for part in participants]
					if len(names) >= 2:
						tie_names = names[:2]
					elif names:
						tie_names = [names[0], names[0]]
					else:
						tie_names = ["Trainer", "Trainer"]
					if hasattr(self, "_format_default_message"):
						message = self._format_default_message(
							"tieBattle", {"[TRAINER]": tie_names}
						)
					else:
						message = _format_result_message("tieBattle", tie_names)
				if message:
					self.log_action(message)
				setattr(self, "_result_logged", True)
			return winner
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
