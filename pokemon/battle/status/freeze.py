from __future__ import annotations

"""Freeze status implementation."""

import random

from .status_core import (
	STATUS_FREEZE,
	StatusCondition,
	can_apply_status,
	has_ability,
	has_type,
)

_SUN_WEATHER = {'harshsunlight', 'extremelyharshsunlight', 'desolateland'}


def _sunlight_active(pokemon, battle) -> bool:
	field = None
	if battle:
		field = getattr(battle, 'field', None)
	if field is None:
		field = getattr(pokemon, 'field', None)
	weather = str(getattr(field, 'weather', '') or '').lower()
	return weather in _SUN_WEATHER


def _move_thaws(move) -> bool:
	if not move:
		return False
	move_type = getattr(move, 'type', None)
	if isinstance(move_type, str) and move_type.lower() == 'fire':
		return True
	raw = getattr(move, 'raw', None)
	if isinstance(raw, dict) and raw.get('thawsTarget'):
		return True
	return bool(getattr(move, 'thaws_target', False))


class Freeze(StatusCondition):
	name = STATUS_FREEZE
	volatile = False

	IMMUNE_ABILITIES = ('magma armor', 'comatose')

	def at_apply(self, pokemon, battle, *, source=None, effect=None, previous=None, allow_self_inflict=False, **kwargs) -> bool:
		if has_type(pokemon, 'ice'):
			return False
		if has_ability(pokemon, self.IMMUNE_ABILITIES):
			return False
		if _sunlight_active(pokemon, battle):
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
		if random.random() < 0.2:
			pokemon.status = 0
			return True
		return False

	def on_hit_by_move(self, pokemon, move, battle) -> None:
		if _move_thaws(move):
			pokemon.status = 0
		return None
