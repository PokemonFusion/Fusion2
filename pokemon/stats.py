from __future__ import annotations

"""Utilities for experience, EV handling and stat calculation."""

from typing import Dict

from .dex import POKEDEX
from .generation import NATURES

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
]


def exp_for_level(level: int, rate: str = "medium_fast") -> int:
    """Return the experience required for the given level."""
    level = max(1, min(level, 100))
    match rate:
        case "fast":
            return int(4 * level ** 3 / 5)
        case "slow":
            return int(5 * level ** 3 / 4)
        case "medium_slow":
            return int(1.2 * level ** 3 - 15 * level ** 2 + 100 * level - 140)
        case _:
            # medium_fast by default
            return level ** 3


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

    if hasattr(pokemon, "total_exp"):
        pokemon.total_exp = getattr(pokemon, "total_exp", 0) + amount
        growth = rate or getattr(pokemon, "growth_rate", None)
        if growth is None:
            growth = getattr(getattr(pokemon, "data", {}), "get", lambda x, d=None: d)(
                "growth_rate", "medium_fast"
            )
            if hasattr(pokemon, "data") and isinstance(pokemon.data, dict):
                growth = pokemon.data.get("growth_rate", "medium_fast")
        # level property will derive from total_exp
    else:
        pokemon.experience = getattr(pokemon, "experience", 0) + amount
        growth = rate or getattr(pokemon, "growth_rate", None)
        if growth is None:
            growth = getattr(getattr(pokemon, "data", {}), "get", lambda x, d=None: d)(
                "growth_rate", "medium_fast"
            )
            if hasattr(pokemon, "data") and isinstance(pokemon.data, dict):
                growth = pokemon.data.get("growth_rate", "medium_fast")
        pokemon.level = level_for_exp(pokemon.experience, growth)

    new_level = getattr(pokemon, "level", None)
    if prev_level is not None and new_level and new_level > prev_level:
        if hasattr(pokemon, "learn_level_up_moves"):
            try:
                pokemon.learn_level_up_moves(caller=caller, prompt=True)
            except TypeError:
                pokemon.learn_level_up_moves()


def add_evs(pokemon, gains: Dict[str, int]) -> None:
    """Apply EV gains to ``pokemon`` respecting limits."""
    evs = dict(getattr(pokemon, "evs", {}) or {})
    total = sum(evs.values())
    for stat, val in gains.items():
        if stat not in ("hp", "atk", "def", "spa", "spd", "spe"):
            continue
        if total >= EV_LIMIT:
            break
        current = evs.get(stat, 0)
        allowed = min(val, STAT_EV_LIMIT - current, EV_LIMIT - total)
        if allowed <= 0:
            continue
        evs[stat] = current + allowed
        total += allowed
    pokemon.evs = evs


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


def calculate_stats(species_name: str, level: int, ivs: Dict[str, int], evs: Dict[str, int], nature: str) -> Dict[str, int]:
    """Return calculated stats for the given Pokémon parameters."""
    species = (
        POKEDEX.get(species_name)
        or POKEDEX.get(species_name.capitalize())
        or POKEDEX.get(species_name.lower())
    )
    if not species:
        raise ValueError(f"Species '{species_name}' not found")
    ivs = {k: ivs.get(k, 0) for k in ("hp", "atk", "def", "spa", "spd", "spe")}
    evs = {k: evs.get(k, 0) for k in ("hp", "atk", "def", "spa", "spd", "spe")}
    stats = {
        "hp": _calc_stat(species.base_stats.hp, ivs["hp"], evs["hp"], level, is_hp=True),
        "atk": _calc_stat(
            species.base_stats.atk,
            ivs["atk"],
            evs["atk"],
            level,
            nature_mod=_nature_mod(nature, "atk"),
        ),
        "def": _calc_stat(
            species.base_stats.def_,
            ivs["def"],
            evs["def"],
            level,
            nature_mod=_nature_mod(nature, "def"),
        ),
        "spa": _calc_stat(
            species.base_stats.spa,
            ivs["spa"],
            evs["spa"],
            level,
            nature_mod=_nature_mod(nature, "spa"),
        ),
        "spd": _calc_stat(
            species.base_stats.spd,
            ivs["spd"],
            evs["spd"],
            level,
            nature_mod=_nature_mod(nature, "spd"),
        ),
        "spe": _calc_stat(
            species.base_stats.spe,
            ivs["spe"],
            evs["spe"],
            level,
            nature_mod=_nature_mod(nature, "spe"),
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
        add_experience(mon, gained)
        if ev_gains:
            add_evs(mon, ev_gains)
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
        add_experience(mons[0], amount)
        if ev_gains:
            add_evs(mons[0], ev_gains)
        if hasattr(mons[0], "save"):
            try:
                mons[0].save()
            except Exception:
                pass

