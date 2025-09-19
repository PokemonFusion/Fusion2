from __future__ import annotations

"""Paralysis status implementation."""

import random

from .status_core import (
	STATUS_PARALYSIS,
	StatusCondition,
	can_apply_status,
	has_ability,
	has_type,
)


class Paralysis(StatusCondition):
	name = STATUS_PARALYSIS
	volatile = False

	IMMUNE_ABILITIES = ('limber',)

	def at_apply(self, pokemon, battle, *, source=None, effect=None, previous=None, allow_self_inflict=False, **kwargs) -> bool:
		if has_type(pokemon, 'electric'):
			return False
		if has_ability(pokemon, self.IMMUNE_ABILITIES):
			return False
		return can_apply_status(
			pokemon,
			self.name,
			battle=battle,
			source=source,
			effect=effect,
			allow_self_inflict=allow_self_inflict,
			previous=previous,
		)

	def on_before_move(self, pokemon, battle) -> bool:
		if random.random() < 0.25:
			if hasattr(pokemon, 'tempvals'):
				pokemon.tempvals['cant_move'] = 'par'
			return False
		return True

	def speed_mod(self, pokemon) -> float:
		return 0.5
