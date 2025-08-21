from __future__ import annotations

"""Utilities for experience, EV handling and stat calculation."""

import importlib
from typing import Dict

_helpers_mod = None


def _get_helpers_module():
	global _helpers_mod
	if _helpers_mod is None:
		try:
			_helpers_mod = importlib.import_module("pokemon.helpers.pokemon_helpers")
		except Exception:  # pragma: no cover - helpers optional
			_helpers_mod = None
	return _helpers_mod


from pokemon.services.move_management import learn_level_up_moves
from pokemon.utils.boosts import ALL_STATS, STAT_KEY_MAP

from ..data.generation import NATURES
from ..dex import POKEDEX

DISPLAY_STAT_MAP = {
	"hp": "HP",
	"attack": "Atk",
	"defense": "Def",
	"special_attack": "SpA",
	"special_defense": "SpD",
	"speed": "Spe",
}

# EV limits
EV_LIMIT = 510
STAT_EV_LIMIT = 252

__all__ = [
	"exp_for_level",
	"level_for_exp",
	"add_experience",
	"add_evs",
	"calculate_stats",
	"distribute_experience",
	"award_experience_to_party",
	"apply_item_exp_mod",
	"apply_item_ev_mod",
]


def exp_for_level(level: int, rate: str = "medium_fast") -> int:
	"""Return the experience required for the given level."""
	level = max(1, min(level, 100))
	match rate:
		case "fast":
			return int(4 * level**3 / 5)
		case "slow":
			return int(5 * level**3 / 4)
		case "medium_slow":
			return int(1.2 * level**3 - 15 * level**2 + 100 * level - 140)
		case _:
			# medium_fast by default
			return level**3


def level_for_exp(exp: int, rate: str = "medium_fast") -> int:
	"""Return the level for the given experience total."""
	level = 1
	for lvl in range(1, 101):
		if exp >= exp_for_level(lvl, rate):
			level = lvl
		else:
			break
	return level


def add_experience(pokemon, amount: int, *, rate: str | None = None, caller=None) -> None:
	"""Add experience to ``pokemon`` and update its level."""
	if amount <= 0:
		return

	prev_level = getattr(pokemon, "level", None)

	def _get_growth_rate(poke) -> str:
		if rate:
			return rate
		growth = getattr(poke, "growth_rate", None)
		if growth:
			return growth
		name = getattr(poke, "species", getattr(poke, "name", None))
		if name:
			species = POKEDEX.get(name) or POKEDEX.get(str(name).lower()) or POKEDEX.get(str(name).capitalize())
			if species:
				return species.raw.get("growthRate", "medium_fast")
		return "medium_fast"

	if hasattr(pokemon, "total_exp"):
		pokemon.total_exp = getattr(pokemon, "total_exp", 0) + amount
		growth = _get_growth_rate(pokemon)
		if hasattr(pokemon, "level"):
			pokemon.level = level_for_exp(pokemon.total_exp, growth)
	else:
		pokemon.experience = getattr(pokemon, "experience", 0) + amount
		growth = _get_growth_rate(pokemon)
		pokemon.level = level_for_exp(pokemon.experience, growth)

	new_level = getattr(pokemon, "level", None)
	if prev_level is not None and new_level and new_level > prev_level:
		try:
			learn_level_up_moves(pokemon, caller=caller, prompt=True)
		except TypeError:
			learn_level_up_moves(pokemon)

	if prev_level is not None and new_level != prev_level:
		mod = _get_helpers_module()
		if mod and hasattr(mod, "refresh_stats"):
			try:
				mod.refresh_stats(pokemon)
			except Exception:  # pragma: no cover - safe fallback
				pass


def add_evs(pokemon, gains: Dict[str, int]) -> None:
	"""Apply EV gains to ``pokemon`` respecting limits."""

	evs_attr = getattr(pokemon, "evs", {}) or {}
	if isinstance(evs_attr, dict):
		evs = {STAT_KEY_MAP.get(k, k): v for k, v in evs_attr.items()}
	else:
		evs = {
			"hp": evs_attr[0],
			"attack": evs_attr[1],
			"defense": evs_attr[2],
			"special_attack": evs_attr[3],
			"special_defense": evs_attr[4],
			"speed": evs_attr[5],
		}

	total = sum(evs.values())
	for stat, val in gains.items():
		full = STAT_KEY_MAP.get(stat, stat)
		if full not in ALL_STATS:
			continue
		if total >= EV_LIMIT:
			break
		current = evs.get(full, 0)
		allowed = min(val, STAT_EV_LIMIT - current, EV_LIMIT - total)
		if allowed <= 0:
			continue
		evs[full] = current + allowed
		total += allowed
	pokemon.evs = evs
	mod = _get_helpers_module()
	if mod and hasattr(mod, "refresh_stats"):
		try:
			mod.refresh_stats(pokemon)
		except Exception:  # pragma: no cover - safe fallback
			pass


def _nature_mod(nature: str, stat: str) -> float:
	inc, dec = NATURES.get(nature, (None, None))
	if stat == inc:
		return 1.1
	if stat == dec:
		return 0.9
	return 1.0


def _calc_stat(base: int, iv: int, ev: int, level: int, *, nature_mod: float = 1.0, is_hp: bool = False) -> int:
	if is_hp:
		return int(((2 * base + iv + ev // 4) * level) / 100) + level + 10
	stat = int(((2 * base + iv + ev // 4) * level) / 100) + 5
	return int(stat * nature_mod)


def _item_name(item) -> str:
	"""Return a normalized name for a held item."""
	if not item:
		return ""
	if isinstance(item, str):
		return item.replace(" ", "").lower()
	return str(getattr(item, "name", "")).replace(" ", "").lower()


def apply_item_exp_mod(pokemon, amount: int) -> int:
	"""Apply experience modifiers from a Pokémon's held item."""
	item_obj = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
	if hasattr(item_obj, "call"):
		try:
			mod = item_obj.call("onModifyExp", amount, pokemon=pokemon)
			if isinstance(mod, (int, float)):
				amount = int(mod)
		except Exception:
			pass
	item = _item_name(item_obj)
	if item == "luckyegg":
		return int(amount * 1.5)
	return amount


def apply_item_ev_mod(pokemon, gains: Dict[str, int]) -> Dict[str, int]:
	"""Apply EV modifiers from a Pokémon's held item."""
	item_obj = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
	item = _item_name(item_obj)
	if not gains:
		return gains
	if hasattr(item_obj, "call"):
		try:
			mod = item_obj.call("onModifyEVs", gains, pokemon=pokemon)
			if isinstance(mod, dict):
				gains = mod
		except Exception:
			pass
	if item == "machobrace":
		gains = {k: v * 2 for k, v in gains.items()}
	power_items = {
		"powerweight": "hp",
		"powerbracer": "attack",
		"powerbelt": "defense",
		"powerlens": "special_attack",
		"powerband": "special_defense",
		"poweranklet": "speed",
	}
	if item in power_items:
		stat = power_items[item]
		mod = gains.copy()
		mod[stat] = mod.get(stat, 0) + 8
		gains = mod
	return {STAT_KEY_MAP.get(k, k): v for k, v in gains.items()}


def calculate_stats(
	species_name: str, level: int, ivs: Dict[str, int], evs: Dict[str, int], nature: str
) -> Dict[str, int]:
	"""Return calculated stats for the given Pokémon parameters."""

	species = POKEDEX.get(species_name) or POKEDEX.get(species_name.capitalize()) or POKEDEX.get(species_name.lower())
	if not species:
		raise ValueError(f"Species '{species_name}' not found")

	ivs = {STAT_KEY_MAP.get(k, k): v for k, v in ivs.items()}
	evs = {STAT_KEY_MAP.get(k, k): v for k, v in evs.items()}
	ivs = {stat: ivs.get(stat, 0) for stat in ALL_STATS}
	evs = {stat: evs.get(stat, 0) for stat in ALL_STATS}

	stats = {
		"hp": _calc_stat(species.base_stats.hp, ivs["hp"], evs["hp"], level, is_hp=True),
		"attack": _calc_stat(
			species.base_stats.attack,
			ivs["attack"],
			evs["attack"],
			level,
			nature_mod=_nature_mod(nature, "attack"),
		),
		"defense": _calc_stat(
			species.base_stats.defense,
			ivs["defense"],
			evs["defense"],
			level,
			nature_mod=_nature_mod(nature, "defense"),
		),
		"special_attack": _calc_stat(
			species.base_stats.special_attack,
			ivs["special_attack"],
			evs["special_attack"],
			level,
			nature_mod=_nature_mod(nature, "special_attack"),
		),
		"special_defense": _calc_stat(
			species.base_stats.special_defense,
			ivs["special_defense"],
			evs["special_defense"],
			level,
			nature_mod=_nature_mod(nature, "special_defense"),
		),
		"speed": _calc_stat(
			species.base_stats.speed,
			ivs["speed"],
			evs["speed"],
			level,
			nature_mod=_nature_mod(nature, "speed"),
		),
	}

	return stats


def distribute_experience(pokemon_list, amount: int, ev_gains: Dict[str, int] | None = None) -> None:
	"""Distribute experience and EVs evenly across ``pokemon_list``."""

	mons = list(pokemon_list)
	if not mons or amount <= 0:
		return

	share = amount // len(mons)
	remainder = amount % len(mons)
	ev_gains = ev_gains or {}

	for idx, mon in enumerate(mons):
		gained = share + (1 if idx < remainder else 0)
		gained = apply_item_exp_mod(mon, gained)
		add_experience(mon, gained)
		if ev_gains:
			add_evs(mon, apply_item_ev_mod(mon, ev_gains))
		if hasattr(mon, "save"):
			try:
				mon.save()
			except Exception:
				pass


def award_experience_to_party(player, amount: int, ev_gains: Dict[str, int] | None = None) -> None:
	"""Award experience to a player's active party respecting EXP Share."""

	storage = getattr(player, "storage", None)
	if not storage or not hasattr(storage.active_pokemon, "all"):
		return

	mons = storage.get_party() if hasattr(storage, "get_party") else list(storage.active_pokemon.all())
	if not mons:
		return

	if getattr(getattr(player, "db", {}), "exp_share", False):
		distribute_experience(mons, amount, ev_gains)
	else:
		gained = apply_item_exp_mod(mons[0], amount)
		add_experience(mons[0], gained)
		if ev_gains:
			add_evs(mons[0], apply_item_ev_mod(mons[0], ev_gains))
		if hasattr(mons[0], "save"):
			try:
				mons[0].save()
			except Exception:
				pass
