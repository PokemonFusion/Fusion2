from __future__ import annotations

"""Utilities for experience, EV handling and stat calculation."""

from typing import Dict, Iterable, List, Mapping, Sequence


def _invalidate_stat_cache(pokemon) -> None:
                """Remove any manually stored stat cache on ``pokemon``.

                The previous implementation recomputed and cached stats whenever
                a change occurred.  Since automatic caching has been disabled, we
                simply drop the ``_cached_stats`` attribute if it exists so future
                stat lookups are freshly calculated.
                """

                try:
                                delattr(pokemon, "_cached_stats")
                except Exception:
                                setattr(pokemon, "_cached_stats", None)


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
						species = POKEDEX.get(name) or POKEDEX.get(str(name).lower()) or \
								POKEDEX.get(str(name).capitalize())
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
				_invalidate_stat_cache(pokemon)


def add_evs(pokemon, gains: Mapping[str, int]) -> None:
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
		_invalidate_stat_cache(pokemon)


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


def _mon_identifier(mon) -> str | None:
        """Return the best identifier for ``mon`` for participation mapping."""

        for attr in ("unique_id", "model_id", "id"):
                value = getattr(mon, attr, None)
                if value is not None:
                        return str(value)
        return None


def _is_fainted(mon) -> bool:
        """Return ``True`` if ``mon`` is fainted based on available fields."""

        for attr in ("current_hp", "hp"):
                hp = getattr(mon, attr, None)
                if hp is not None:
                        return hp <= 0
        return False


def _format_reward_message(mon, exp_amount: int, ev_values: Mapping[str, int]) -> str | None:
        """Return a human-readable reward summary for ``mon``."""

        if not exp_amount and not any(ev_values.values()):
                return None
        name = (
                getattr(mon, "nickname", None)
                or getattr(mon, "name", None)
                or getattr(mon, "species", None)
                or "Pokemon"
        )
        parts: List[str] = []
        if exp_amount:
                parts.append(f"{exp_amount} EXP")
        if any(ev_values.values()):
                ev_parts = []
                for stat, value in ev_values.items():
                        if not value:
                                continue
                        label = DISPLAY_STAT_MAP.get(stat, stat.title())
                        ev_parts.append(f"{label} +{value}")
                if ev_parts:
                        parts.append(f"EVs: {', '.join(ev_parts)}")
        detail = " and ".join(parts)
        return f"{name} gained {detail}!"


def _notify_winner(player, caller, messages: Sequence[str]) -> None:
        """Notify the winner about obtained experience and EVs."""

        if not messages:
                return
        def _emit(recipient, attr: str, message: str) -> None:
                if not recipient or not hasattr(recipient, attr):
                        return
                try:
                        getattr(recipient, attr)(message)
                except Exception:
                        pass

        target = caller if caller and hasattr(caller, "log_action") else None
        fallback = None if target else player

        for msg in messages:
                if not msg:
                        continue
                if target:
                        _emit(target, "log_action", msg)
                elif fallback:
                        _emit(fallback, "msg", msg)
                else:
                        print(msg)


def _resolve_participants(
        party: Sequence,
        participants: Iterable | None,
) -> List:
        """Return the list of party Pokémon that actively participated."""

        if not participants:
                return []
        party_by_id = {
                ident: mon for mon in party if (ident := _mon_identifier(mon))
        }
        used: set = set()
        resolved: List = []
        for battle_mon in participants:
                if _is_fainted(battle_mon):
                        continue
                identifier = _mon_identifier(battle_mon)
                target = None
                if identifier and identifier in party_by_id:
                        target = party_by_id[identifier]
                else:
                        for candidate in party:
                                if candidate in used:
                                        continue
                                if _is_fainted(candidate):
                                        continue
                                target = candidate
                                break
                if target is None:
                        continue
                if target in used:
                        continue
                used.add(target)
                resolved.append(target)
        return resolved


def award_experience_to_party(
        player,
        amount: int,
        ev_gains: Dict[str, int] | None = None,
        *,
        participants: Iterable | None = None,
        caller=None,
) -> None:
        """Award experience/EVs to a player's party using EXP Share rules."""

        storage = getattr(player, "storage", None)
        if not storage or not hasattr(storage.active_pokemon, "all"):
                return

        mons = (
                storage.get_party()
                if hasattr(storage, "get_party")
                else list(storage.active_pokemon.all())
        )
        if not mons:
                return

        ev_gains = ev_gains or {}
        share_enabled = bool(getattr(getattr(player, "db", {}), "exp_share", False))

        participant_mons = _resolve_participants(mons, participants)
        # If participation could not be resolved fall back to the first healthy
        # Pokémon so rewards are not lost.
        if not participant_mons and amount and mons:
                fallback = [mon for mon in mons if not _is_fainted(mon)]
                if fallback:
                        participant_mons = [fallback[0]]

        participant_messages: List[str] = []
        non_participant_messages: List[str] = []

        if participant_mons:
                share, remainder = divmod(amount, len(participant_mons))
                for idx, mon in enumerate(participant_mons):
                        gained = share + (1 if idx < remainder else 0)
                        gained = apply_item_exp_mod(mon, gained)
                        if gained:
                                add_experience(mon, gained, caller=caller)
                        if ev_gains:
                                ev_payload = apply_item_ev_mod(mon, ev_gains)
                                add_evs(mon, ev_payload)
                        else:
                                ev_payload = {}
                        message = _format_reward_message(mon, gained, ev_payload)
                        if message:
                                participant_messages.append(message)
                        if hasattr(mon, "save"):
                                try:
                                        mon.save()
                                except Exception:
                                        pass

        recipients = set(participant_mons)
        if share_enabled:
                # Determine the base amount awarded to participants to derive
                # the EXP Share payout for the rest of the party.
                if participant_mons:
                        base_amount = amount // len(participant_mons)
                else:
                        base_amount = amount // max(len(mons), 1)
                shared_gain = base_amount // 2
                extras = [
                        mon
                        for mon in mons
                        if mon not in recipients and not _is_fainted(mon)
                ]
                for mon in extras:
                        gained = apply_item_exp_mod(mon, shared_gain)
                        if gained:
                                add_experience(mon, gained, caller=caller)
                        if ev_gains:
                                ev_payload = apply_item_ev_mod(mon, ev_gains)
                                add_evs(mon, ev_payload)
                        else:
                                ev_payload = {}
                        if gained or any(ev_payload.values()):
                                message = _format_reward_message(mon, gained, ev_payload)
                                if message:
                                        non_participant_messages.append(message)
                        if hasattr(mon, "save"):
                                try:
                                        mon.save()
                                except Exception:
                                        pass

        _notify_winner(player, caller, participant_messages + non_participant_messages)
