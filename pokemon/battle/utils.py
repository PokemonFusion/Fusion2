"""Utility helpers for the battle engine.

This module provides a small collection of helpers used by the battle
simulation.  Historically ``apply_boost`` lived in a higher level module
(``pokemon.utils.boosts``) so tests that only stub out
``pokemon.battle.utils`` failed with an :class:`ImportError`.  Re-exporting
``apply_boost`` here keeps the public API stable while avoiding a hard
dependency on the original module in calling code.
"""

from typing import Dict, Optional

from pokemon.utils.boosts import STAT_KEY_MAP, apply_boost as _apply_boost


def _safe_get_stats(pokemon) -> Dict[str, int]:
	"""Return a stats dictionary for ``pokemon`` with graceful fallback.

	The standard :func:`pokemon.helpers.pokemon_helpers.get_stats` helper is
	used when available.  If that import or call fails, the function falls
	back to the Pokémon's ``base_stats`` attribute, ensuring that callers
	always receive a dictionary of stat values.
	"""

	try:  # pragma: no cover - import error path
		from pokemon.helpers.pokemon_helpers import get_stats

		return get_stats(pokemon)
	except Exception:  # pragma: no cover - broad fallback
		base = getattr(pokemon, "base_stats", None)
		if isinstance(base, dict):
			return {STAT_KEY_MAP.get(k, k): v for k, v in base.items()}
		return {name: getattr(base, name, 0) if base else 0 for name in STAT_KEY_MAP.values()}


def get_modified_stat(pokemon, stat: str) -> int:
	"""Return a stat value after applying temporary boosts."""

	stat = STAT_KEY_MAP.get(stat, stat)
	base = _safe_get_stats(pokemon).get(stat, 0)
	boosts = getattr(pokemon, "boosts", {})
	if isinstance(boosts, dict):
		boosts = {STAT_KEY_MAP.get(k, k): v for k, v in boosts.items()}
		pokemon.boosts = boosts
		stage = boosts.get(stat, 0)
	else:
		stage = getattr(boosts, stat, 0)

	if stat in {"accuracy", "evasion"}:
		if stage >= 0:
			modifier = (3 + stage) / 3
		else:
			modifier = 3 / (3 - stage)
	else:
		if stage >= 0:
			modifier = (2 + stage) / 2
		else:
			modifier = 2 / (2 - stage)
	return int(base * modifier)


def is_self_target(target: Optional[str]) -> bool:
	"""Return ``True`` if ``target`` refers to the user or its allies.

	The battle engine simplifies targeting by treating moves that would
	normally affect an ally (such as ``"adjacentAlly"``) as if they target
	the user when no ally is present.  This helper centralises that logic so
	callers can easily determine whether a move's effects should apply to the
	user or to their opponent.
	"""

	return target in {"self", "adjacentAlly", "adjacentAllyOrSelf", "ally"}


def apply_boost(pokemon, boosts, source=None, effect=None) -> None:
	"""Apply stat stage changes to ``pokemon``.

	This thin wrapper forwards to :func:`pokemon.utils.boosts.apply_boost`
	so that the battle engine can import :mod:`pokemon.battle.utils` for
	all battle-related helpers without referencing the broader utilities
	module directly.  The parameters are passed through unchanged.

	Parameters
	----------
	pokemon: Any
	    The Pokémon receiving the boost.
	boosts: dict | None
	    Mapping of stat identifiers to stage deltas.
	source, effect: Any, optional
	    Additional context forwarded to ability callbacks.
	"""

	_apply_boost(pokemon, boosts, source=source, effect=effect)


__all__ = ["get_modified_stat", "is_self_target", "apply_boost"]
