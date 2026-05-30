"""Shared helpers for stat mappings and temporary boosts.

This module provides a minimal set of utilities that are used by both the
battle engine and the dex move/ability callbacks.  Importing from here keeps
higher-level modules decoupled and avoids circular imports between the battle
and dex packages.
"""

from typing import Dict, Optional

# Mapping of shorthand stat names to their canonical attribute names.
STAT_KEY_MAP = {
	"hp": "hp",
	"atk": "attack",
	"def": "defense",
	"spa": "special_attack",
	"spd": "special_defense",
	"spe": "speed",
}

REVERSE_STAT_KEY_MAP = {v: k for k, v in STAT_KEY_MAP.items()}
ALL_STATS = list(STAT_KEY_MAP.values())


def apply_boost(
	pokemon,
	boosts: Optional[Dict[str, int]],
	source=None,
	effect=None,
) -> None:
	"""Apply stat stage changes to ``pokemon``.

	Parameters
	----------
	pokemon: Any
	    The Pokémon receiving the boost.
	boosts: dict | None
	    Mapping of stat keys to stage changes.  ``None`` or an empty mapping
	    results in no change but still triggers ``onTryBoost`` and
	    ``onChangeBoost`` callbacks.
	source, effect: Any, optional
	    Additional context forwarded to ability callbacks.

	The provided ``boosts`` mapping uses short stat identifiers (e.g.
	``"atk"``, ``"spe"``).  Existing boosts are normalised using
	:data:`STAT_KEY_MAP` and each stage change is clamped between -6 and 6.
	"""

	boosts = dict(boosts or {})
	battle = getattr(pokemon, "battle", None)

	if battle is not None and hasattr(battle, "runEvent"):
		changed = battle.runEvent("ChangeBoost", pokemon, source, effect, dict(boosts))
		if changed is False:
			return
		if isinstance(changed, dict):
			boosts = dict(changed)
		tried = battle.runEvent("TryBoost", pokemon, source, effect, dict(boosts))
		if tried is False:
			return
		if isinstance(tried, dict):
			boosts = dict(tried)
	else:
		ability = getattr(pokemon, "ability", None)
		if ability and hasattr(ability, "call"):
			try:
				ability.call("onTryBoost", boosts, target=pokemon, source=source, effect=effect)
				ability.call(
					"onChangeBoost",
					boosts,
					target=pokemon,
					source=source,
					effect=effect,
				)
			except Exception:  # pragma: no cover - ability callbacks are optional
				pass

	current = getattr(pokemon, "boosts", {}) or {}
	if not isinstance(current, dict):  # pragma: no cover - defensive
		current = {}

	# normalise existing keys
	current = {STAT_KEY_MAP.get(k, k): v for k, v in current.items()}

	applied_changes: Dict[str, int] = {}
	for stat, amount in boosts.items():
		full = STAT_KEY_MAP.get(stat, stat)
		cur = current.get(full, 0)
		new_val = max(-6, min(6, cur + amount))
		current[full] = new_val
		applied_changes[REVERSE_STAT_KEY_MAP.get(full, full)] = new_val - cur

	pokemon.boosts = current

	if battle is not None and hasattr(battle, "runEvent"):
		battle.runEvent("AfterEachBoost", pokemon, source, effect, dict(applied_changes))
		battle.runEvent("AfterBoost", pokemon, source, effect, dict(applied_changes))
	else:
		ability = getattr(pokemon, "ability", None)
		# Trigger post-boost ability hooks so abilities can react to the final
		# stage values.  Errors are ignored as ability callbacks are optional.
		if ability and hasattr(ability, "call"):
			try:
				ability.call(
					"onAfterEachBoost",
					boosts,
					target=pokemon,
					source=source,
					effect=effect,
				)
			except Exception:  # pragma: no cover - ability callbacks are optional
				pass


__all__ = ["STAT_KEY_MAP", "REVERSE_STAT_KEY_MAP", "ALL_STATS", "apply_boost"]
