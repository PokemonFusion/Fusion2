from __future__ import annotations

"""Sleep status implementation."""

import random

from .status_core import (
        STATUS_SLEEP,
        StatusCondition,
        _log_terrain_block,
        can_apply_status,
        has_ability,
        iter_allies,
)


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


def _active_uproar(battle) -> bool:
	for participant in getattr(battle, 'participants', []):
		for mon in getattr(participant, 'active', []):
			if getattr(mon, 'volatiles', {}).get('uproar'):
				return True
	return False


def _terrain_blocks_sleep(pokemon, battle) -> bool:
        field = None
        if battle:
                field = getattr(battle, 'field', None)
        if field is None:
                field = getattr(pokemon, 'field', None)
        terrain = str(getattr(field, 'terrain', '') or '')
        terrain_key = terrain.replace(' ', '').replace('-', '').lower()
        if terrain_key == 'electricterrain' and _is_grounded(pokemon):
                _log_terrain_block(pokemon, battle, terrain_key)
                return True
        return False


class Sleep(StatusCondition):
	name = STATUS_SLEEP
	volatile = False

	IMMUNE_ABILITIES = ('insomnia', 'vital spirit', 'sweet veil', 'comatose')
	TEAM_ABILITIES = ('sweet veil',)

	def _has_team_immunity(self, pokemon, battle) -> bool:
		for ally in iter_allies(pokemon, battle):
			if has_ability(ally, self.TEAM_ABILITIES):
				return True
		return False

	def at_apply(self, pokemon, battle, *, source=None, effect=None, previous=None, allow_self_inflict=False, **kwargs) -> bool:
		if has_ability(pokemon, self.IMMUNE_ABILITIES):
			return False
		if self._has_team_immunity(pokemon, battle):
			return False
		if _terrain_blocks_sleep(pokemon, battle):
			return False
		if battle and _active_uproar(battle):
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

	def on_start(self, pokemon, battle, *, effect=None, **kwargs) -> None:
		if not hasattr(pokemon, 'tempvals'):
			setattr(pokemon, 'tempvals', {})
		via_rest = isinstance(effect, str) and effect.startswith('move:rest')
		turns = 2 if via_rest else random.randint(1, 3)
		pokemon.tempvals['sleep_turns'] = turns
		return None

	def on_before_move(self, pokemon, battle) -> bool:
		tempvals = getattr(pokemon, 'tempvals', {})
		turns = tempvals.get('sleep_turns')
		if turns is None:
			return True
		if turns <= 0:
			pokemon.tempvals.pop('sleep_turns', None)
			pokemon.status = 0
			if battle:
				battle.announce_status_change(
					pokemon,
					self.name,
					event="end",
				)
			return True
		pokemon.tempvals['sleep_turns'] = turns - 1
		can_act = getattr(pokemon, 'can_use_while_asleep', None)
		if callable(can_act) and can_act():
			return True
		if battle:
			battle.announce_status_change(
				pokemon,
				self.name,
				event="cant",
			)
		return False
