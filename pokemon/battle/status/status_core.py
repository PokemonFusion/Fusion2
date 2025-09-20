from __future__ import annotations

"""Core helpers for battle status conditions."""

from typing import Iterator, Sequence


__all__ = [
	'StatusCondition',
	'can_apply_status',
	'has_ability',
	'has_type',
	'iter_allies',
	'STATUS_BURN',
	'STATUS_POISON',
	'STATUS_TOXIC',
	'STATUS_PARALYSIS',
	'STATUS_SLEEP',
	'STATUS_FREEZE',
]


STATUS_BURN = 'brn'
STATUS_POISON = 'psn'
STATUS_TOXIC = 'tox'
STATUS_PARALYSIS = 'par'
STATUS_SLEEP = 'slp'
STATUS_FREEZE = 'frz'


def _normalize_name(value: object) -> str:
	"""Return a lowercase string representation of *value*."""
	if value is None:
		return ''
	if isinstance(value, str):
		normalized = value.strip().lower()
		if normalized in {"", "0", "none"}:
			return ""
		return normalized
	for attr in ('name', 'id', 'key'):
		attr_val = getattr(value, attr, None)
		if attr_val:
			normalized = str(attr_val).strip().lower()
			if normalized in {"", "0", "none"}:
				return ""
			return normalized
	normalized = str(value).strip().lower()
	if normalized in {"", "0", "none"}:
		return ""
	return normalized


def _make_name_set(names: Sequence[str] | str) -> set[str]:
	if isinstance(names, str):
		return {_normalize_name(names)}
	return {_normalize_name(name) for name in names}


def has_ability(holder, names: Sequence[str] | str) -> bool:
	"""Return ``True`` if *holder* has one of *names* as its ability."""
	if holder is None:
		return False
	ability = getattr(holder, 'ability', holder)
	ability_name = _normalize_name(ability)
	return ability_name in _make_name_set(names)


def has_type(pokemon, names: Sequence[str] | str) -> bool:
	"""Return ``True`` if *pokemon* matches any typing in *names*."""
	if pokemon is None:
		return False
	types = getattr(pokemon, 'types', None) or []
	name_set = _make_name_set(names)
	return any(_normalize_name(tp) in name_set for tp in types)


def _get_battle(pokemon, battle=None):
	if battle is not None:
		return battle
	return getattr(pokemon, 'battle', None)


def iter_allies(pokemon, battle=None) -> Iterator:
	"""Yield active allied Pokémon for *pokemon*."""
	battle = _get_battle(pokemon, battle)
	if not battle:
		return iter(())
	side = getattr(pokemon, 'side', None)
	allies = []
	for participant in getattr(battle, 'participants', []):
		for mon in getattr(participant, 'active', []):
			if mon is pokemon:
				continue
			if side and getattr(mon, 'side', None) is side:
				allies.append(mon)
	return iter(allies)


def _get_field(pokemon, battle=None):
	battle = _get_battle(pokemon, battle)
	if battle:
		return getattr(battle, 'field', None)
	return getattr(pokemon, 'field', None)


def _is_grounded(pokemon) -> bool:
	if hasattr(pokemon, 'is_grounded'):
		try:
			return bool(pokemon.is_grounded())
		except TypeError:
			try:
				return bool(pokemon.is_grounded(None))
			except Exception:
				pass
	return bool(getattr(pokemon, 'grounded', True))


def _effect_is_move(effect) -> bool:
	if not effect:
		return False
	if isinstance(effect, str):
		return effect.startswith('move:')
	return bool(getattr(effect, 'is_move', False) or getattr(effect, 'category', None))


def _is_self_inflicted(pokemon, source, effect, allow_self_inflict: bool) -> bool:
	if allow_self_inflict:
		return True
	if source is not None and source is pokemon:
		return True
	if isinstance(effect, str):
		return effect.startswith('item:') or effect.startswith('self:')
	return False


def _blocked_by_misty_terrain(pokemon, battle=None) -> bool:
	field = _get_field(pokemon, battle)
	terrain = _normalize_name(getattr(field, 'terrain', None)) if field else ''
	return terrain == 'mistyterrain' and _is_grounded(pokemon)


def _blocked_by_safeguard(pokemon) -> bool:
	side = getattr(pokemon, 'side', None)
	conditions = getattr(side, 'conditions', {}) if side else {}
	for key in conditions:
		if _normalize_name(key) == 'safeguard':
			return True
	return False


def _blocked_by_substitute(pokemon, source, effect) -> bool:
	if not _effect_is_move(effect):
		return False
	volatiles = getattr(pokemon, 'volatiles', {})
	return any(_normalize_name(key) == 'substitute' for key in volatiles)


def _has_major_status(pokemon) -> bool:
	status = _normalize_name(getattr(pokemon, 'status', None))
	return status not in {'', '0', 'none'}


def can_apply_status(
	target,
	status_name: str,
	*,
	battle=None,
	source=None,
	effect=None,
	allow_self_inflict: bool = False,
	previous=None,
) -> bool:
	"""Return True if the status can be applied to *target*."""
	status_norm = _normalize_name(status_name)
	prev_norm = _normalize_name(previous)
	if prev_norm and prev_norm not in {status_norm, ''}:
		return False
	current = _normalize_name(getattr(target, 'status', None))
	if current and current not in {status_norm, ''}:
		return False
	if has_ability(target, 'purifying salt'):
		return False
	self_inflicted = _is_self_inflicted(target, source, effect, allow_self_inflict)
	if not self_inflicted:
		if _blocked_by_misty_terrain(target, battle):
			return False
		if _blocked_by_safeguard(target):
			return False
		if _blocked_by_substitute(target, source, effect):
			return False
	return True


class StatusCondition:
	"""Base class for non-volatile status conditions."""
	name = 'status'
	volatile = False

	def at_apply(self, pokemon, battle, *, source=None, effect=None, previous=None, allow_self_inflict=False, **kwargs) -> bool:
		"""Return ``True`` if the status should attach to *pokemon*."""
		return True

	def on_start(self, pokemon, battle, **kwargs) -> None:
		"""Called after the status has been attached."""
		return None

	def on_before_move(self, pokemon, battle) -> bool:
		"""Return ``False`` to stop the Pokémon acting this turn."""
		return True

	def on_after_move(self, pokemon, battle) -> None:
		return None

	def on_end_turn(self, pokemon, battle) -> None:
		return None

	def on_switch_out(self, pokemon, battle) -> None:
		return None

	def on_switch_in(self, pokemon, battle) -> None:
		return None

	def on_hit_by_move(self, pokemon, move, battle) -> None:
		return None

	def speed_mod(self, pokemon) -> float:
		"""Return a multiplicative speed modifier."""
		return 1.0

	def modify_attack(self, pokemon, attack_value, move=None):
		"""Return the modified Attack stat for physical moves."""
		return attack_value
