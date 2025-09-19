from __future__ import annotations

"""Burn status condition implementation."""

from .status_core import (
	STATUS_BURN,
	StatusCondition,
	can_apply_status,
	has_ability,
	has_type,
)

_FACADE_MOVES = {'facade'}


def _is_physical(move) -> bool:
	category = getattr(move, 'category', None)
	if category is None and hasattr(move, 'raw'):
		category = getattr(move.raw, 'get', lambda *_: None)('category') if isinstance(move.raw, dict) else None
	return str(category or '').lower() == 'physical'


def _move_name(move) -> str:
	for attr in ('key', 'id', 'name'):
		value = getattr(move, attr, None)
		if value:
			return str(value).lower()
	return ''


class Burn(StatusCondition):
	name = STATUS_BURN
	volatile = False

	def at_apply(self, pokemon, battle, *, source=None, effect=None, previous=None, allow_self_inflict=False, **kwargs) -> bool:
		if has_type(pokemon, 'fire'):
			return False
		if has_ability(pokemon, ('water veil', 'water bubble')):
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

	def on_end_turn(self, pokemon, battle) -> None:
		if has_ability(pokemon, 'magic guard'):
			return None
		max_hp = getattr(pokemon, 'max_hp', getattr(pokemon, 'hp', 0)) or 0
		if max_hp <= 0:
			return None
		divisor = 32 if has_ability(pokemon, 'heatproof') else 16
		damage = max(1, max_hp // divisor)
		pokemon.hp = max(0, getattr(pokemon, 'hp', 0) - damage)
		return None

	def modify_attack(self, pokemon, attack_value, move=None):
		if not move or not _is_physical(move):
			return attack_value
		if has_ability(pokemon, 'guts'):
			return attack_value
		if _move_name(move) in _FACADE_MOVES:
			return attack_value
		return max(1, attack_value // 2)
