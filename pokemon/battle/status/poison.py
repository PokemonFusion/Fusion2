from __future__ import annotations

"""Poison and bad poison status implementations."""

from .status_core import (
	STATUS_POISON,
	STATUS_TOXIC,
	StatusCondition,
	can_apply_status,
	has_ability,
	has_type,
	iter_allies,
	log_status_damage,
)


def _source_has_ability(source, names) -> bool:
	if has_ability(source, names):
		return True
	user = getattr(source, 'user', None)
	if has_ability(user, names):
		return True
	holder = getattr(source, 'source', None)
	if has_ability(holder, names):
		return True
	return False


class Poison(StatusCondition):
	name = STATUS_POISON
	volatile = False

	IMMUNE_ABILITIES = ('immunity', 'pastel veil')
	TEAM_IMMUNITY = ('pastel veil',)

	def _has_team_immunity(self, pokemon, battle) -> bool:
		for ally in iter_allies(pokemon, battle):
			if has_ability(ally, self.TEAM_IMMUNITY):
				return True
		return False

	def at_apply(self, pokemon, battle, *, source=None, effect=None, previous=None, allow_self_inflict=False, **kwargs) -> bool:
		if has_type(pokemon, ('poison', 'steel')) and not _source_has_ability(source, 'corrosion'):
			return False
		if has_ability(pokemon, self.IMMUNE_ABILITIES):
			return False
		if self._has_team_immunity(pokemon, battle):
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
		max_hp = getattr(pokemon, 'max_hp', getattr(pokemon, 'hp', 0)) or 0
		if max_hp <= 0:
			return None
		if has_ability(pokemon, 'poison heal'):
			heal = max(1, max_hp // 8)
			pokemon.hp = min(max_hp, getattr(pokemon, 'hp', 0) + heal)
			return None
		if has_ability(pokemon, 'magic guard'):
			return None
		damage = max(1, max_hp // 8)
		pokemon.hp = max(0, getattr(pokemon, 'hp', 0) - damage)
		log_status_damage(pokemon, battle, STATUS_POISON)
		return None


class BadPoison(StatusCondition):
	name = STATUS_TOXIC
	volatile = False

	IMMUNE_ABILITIES = Poison.IMMUNE_ABILITIES
	TEAM_IMMUNITY = Poison.TEAM_IMMUNITY

	def _has_team_immunity(self, pokemon, battle) -> bool:
		return Poison._has_team_immunity(self, pokemon, battle)

	def at_apply(self, pokemon, battle, *, source=None, effect=None, previous=None, allow_self_inflict=False, **kwargs) -> bool:
		if has_type(pokemon, ('poison', 'steel')) and not _source_has_ability(source, 'corrosion'):
			return False
		if has_ability(pokemon, self.IMMUNE_ABILITIES):
			return False
		if self._has_team_immunity(pokemon, battle):
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

	def on_switch_out(self, pokemon, battle) -> None:
		pokemon.toxic_counter = 0
		return None

	def on_switch_in(self, pokemon, battle) -> None:
		pokemon.toxic_counter = max(1, getattr(pokemon, 'toxic_counter', 1) or 1)
		return None

	def on_end_turn(self, pokemon, battle) -> None:
		max_hp = getattr(pokemon, 'max_hp', getattr(pokemon, 'hp', 0)) or 0
		if max_hp <= 0:
			return None
		counter = getattr(pokemon, 'toxic_counter', 1) or 1
		if has_ability(pokemon, 'poison heal'):
			heal = max(1, max_hp // 8)
			pokemon.hp = min(max_hp, getattr(pokemon, 'hp', 0) + heal)
			pokemon.toxic_counter = counter + 1
			return None
		if has_ability(pokemon, 'magic guard'):
			pokemon.toxic_counter = counter + 1
			return None
		damage = max(1, (max_hp * counter) // 16)
		pokemon.hp = max(0, getattr(pokemon, 'hp', 0) - damage)
		pokemon.toxic_counter = counter + 1
		log_status_damage(pokemon, battle, STATUS_TOXIC)
		return None
