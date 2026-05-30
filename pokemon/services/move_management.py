"""Service functions for managing Pokémon moves.

The project historically stored a fair amount of move related logic on the
``OwnedPokemon`` model.  To keep that model lean and more easily testable,
the behaviour has been moved into this module.  The model now exposes thin
wrappers that delegate to these helpers.
"""

from __future__ import annotations

import logging
from typing import Iterable

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

logger = logging.getLogger(__name__)


def _fallback_normalize_key(val: str) -> str:
	"""Return a normalized move key when battle helpers are unavailable."""

	return val.replace(" ", "").replace("-", "").replace("'", "").lower()


def normalize_move_key(value: str) -> str:
	"""Return the canonical normalized key used for move lookups."""

	try:
		from pokemon.battle.compat import _battle_norm_key as _normalize_key
	except Exception:
		try:
			from pokemon.battle.engine import _normalize_key
		except Exception:
			_normalize_key = _fallback_normalize_key
	return _normalize_key(value)


def _get_movedex():
	"""Return the best available MOVEDEX mapping."""

	import sys

	dex_mod = sys.modules.get("pokemon.dex")
	if dex_mod is None:
		try:
			from pokemon import dex as dex_mod  # type: ignore
		except Exception:
			dex_mod = None
	if dex_mod is not None:
		return getattr(dex_mod, "MOVEDEX", {})
	try:
		from pokemon.dex.moves.movesdex import py_dict

		return py_dict
	except Exception:
		return {}


def _get_move_pp_from_dex(movedex, move_name: str):
	"""Return base PP for ``move_name`` from MOVEDEX-like mappings."""

	keys = []
	for key in (normalize_move_key(move_name), _fallback_normalize_key(move_name), str(move_name or "").lower()):
		if key and key not in keys:
			keys.append(key)
	try:
		from pokemon.battle._shared import _normalize_key as _shared_normalize_key

		shared_key = _shared_normalize_key(move_name)
		if shared_key and shared_key not in keys:
			keys.append(shared_key)
	except Exception:
		pass

	for key in keys:
		entry = movedex.get(key)
		if entry is None:
			continue
		base_pp = getattr(entry, "pp", None)
		if base_pp is None and isinstance(entry, dict):
			base_pp = entry.get("pp")
		if base_pp is not None:
			return key, base_pp
	return "", None


def _move_display_name(move_name: str) -> str:
	"""Return the best display name for a move key or name."""

	raw = str(move_name or "").strip()
	if not raw:
		return ""

	movedex = _get_movedex()
	matched_key, _base_pp = _get_move_pp_from_dex(movedex, raw)
	entry = movedex.get(matched_key) if matched_key else None
	name = getattr(entry, "name", None)
	if name is None and isinstance(entry, dict):
		name = entry.get("name")
	if name:
		return str(name)
	return raw.replace("_", " ").replace("-", " ").title()


def _pokemon_level(pokemon) -> int:
	"""Return the current level for ``pokemon`` without assuming model shape."""

	try:
		level = getattr(pokemon, "computed_level")
	except Exception:
		level = None
	if level is None:
		level = getattr(pokemon, "level", 1)
	try:
		return max(1, int(level or 1))
	except (TypeError, ValueError):
		return 1


def _relation_items(relation, *, order_by: str | None = None) -> list:
	"""Return a relation/list as plain items, optionally ordered."""

	if relation is None:
		return []
	try:
		items = relation.all()
	except AttributeError:
		items = relation
	if order_by and hasattr(items, "order_by"):
		try:
			items = items.order_by(order_by)
		except TypeError:
			items = items.order_by(order_by)
	try:
		return list(items)
	except TypeError:
		return []


def _move_norms(moves) -> set[str]:
	"""Return normalized names for move-like objects or strings."""

	norms: set[str] = set()
	for move in moves or []:
		name = getattr(move, "name", move)
		if name:
			norms.add(normalize_move_key(str(name)))
	return norms


def _active_moveset_slot_names(pokemon) -> list[str]:
	"""Return active moveset slot names for ``pokemon``."""

	active_slots = getattr(pokemon, "activemoveslot_set", None)
	if active_slots is not None:
		slots = _relation_items(active_slots, order_by="slot")
		names = [getattr(getattr(slot, "move", None), "name", "") for slot in slots]
		return [name for name in names if name]

	active_ms = getattr(pokemon, "active_moveset", None)
	if active_ms is not None:
		slots = _relation_items(getattr(active_ms, "slots", None), order_by="slot")
		names = [getattr(getattr(slot, "move", None), "name", "") for slot in slots]
		return [name for name in names if name]
	return []


def _clear_moveset_slots(moveset) -> None:
	"""Remove all slots from ``moveset`` across Django and test doubles."""

	slots = getattr(moveset, "slots", None)
	if slots is None:
		return
	try:
		slots.all().delete()
		return
	except AttributeError:
		pass
	deleter = getattr(slots, "delete", None)
	if callable(deleter):
		deleter()
		return
	clearer = getattr(slots, "clear", None)
	if callable(clearer):
		clearer()


def _save_pokemon(pokemon, *, update_fields: list[str] | None = None) -> None:
	"""Persist ``pokemon`` when possible."""

	saver = getattr(pokemon, "save", None)
	if not callable(saver):
		return
	try:
		if update_fields:
			saver(update_fields=update_fields)
		else:
			saver()
	except TypeError:
		saver()


def level_up_move_names_for_pokemon(pokemon) -> list[str]:
	"""Return all level-up moves available at ``pokemon``'s current level."""

	species = getattr(pokemon, "species", getattr(pokemon, "name", "")) or ""
	level = _pokemon_level(pokemon)

	try:
		from pokemon.middleware import get_moveset_by_name

		_, moveset = get_moveset_by_name(species)
	except Exception:
		moveset = None

	if moveset:
		level_moves = [
			(int(lvl), str(move))
			for lvl, move in moveset.get("level-up", [])
			if int(lvl) <= level
		]
		level_moves.sort(key=lambda row: row[0])
		moves: list[str] = []
		seen: set[str] = set()
		for _lvl, move in level_moves:
			norm = normalize_move_key(move)
			if norm in seen:
				continue
			seen.add(norm)
			moves.append(move)
		return moves

	try:
		from pokemon.data.generation import get_valid_moves

		moves = get_valid_moves(str(species), level)
	except Exception:
		moves = []

	ordered: list[str] = []
	seen: set[str] = set()
	for move in reversed(list(moves or [])):
		norm = normalize_move_key(str(move))
		if norm in seen:
			continue
		seen.add(norm)
		ordered.append(str(move))
	return ordered


def default_active_move_names_for_pokemon(pokemon) -> list[str]:
	"""Return the default generated active moves for ``pokemon``."""

	species = getattr(pokemon, "species", getattr(pokemon, "name", "")) or ""
	level = _pokemon_level(pokemon)
	try:
		from pokemon.data.generation import choose_wild_moves

		moves = choose_wild_moves(str(species), level)
	except Exception:
		moves = []
	if not moves:
		level_moves = level_up_move_names_for_pokemon(pokemon)
		moves = level_moves[-4:]
	if not moves:
		moves = ["Tackle"]
	return list(moves[:4])


def initialize_generated_moveset(
	pokemon,
	*,
	active_move_names: list[str] | tuple[str, ...] | None = None,
	replace_active: bool = True,
) -> dict:
	"""Initialize learned moves and the active moveset for generated PokÃ©mon.

	All level-up moves available at the PokÃ©mon's current level are added to
	``learned_moves``.  The active moveset is then set to ``active_move_names``
	when provided, otherwise to the generated default active four moves.
	"""

	if not pokemon:
		return {"learned": 0, "active": []}

	from pokemon.models.moves import Move

	level_moves = level_up_move_names_for_pokemon(pokemon)
	raw_active_names = list(active_move_names or default_active_move_names_for_pokemon(pokemon))
	active_names: list[str] = []
	active_seen: set[str] = set()
	for move in raw_active_names:
		norm = normalize_move_key(str(move))
		if not norm or norm in active_seen:
			continue
		active_seen.add(norm)
		active_names.append(str(move))
		if len(active_names) >= 4:
			break
	learnable_names = list(level_moves)
	for move in active_names:
		if normalize_move_key(move) not in _move_norms(learnable_names):
			learnable_names.append(move)

	learned_relation = getattr(pokemon, "learned_moves", None)
	known = _move_norms(_relation_items(learned_relation, order_by="name"))
	learned_count = 0
	for move_name in learnable_names:
		display_name = _move_display_name(move_name)
		if not display_name:
			continue
		norm = normalize_move_key(display_name)
		if norm in known:
			continue
		move_obj, _created = Move.objects.get_or_create(name=display_name)
		if learned_relation is not None:
			learned_relation.add(move_obj)
		known.add(norm)
		learned_count += 1

	current_active = _active_moveset_slot_names(pokemon)
	if current_active and not replace_active:
		return {"learned": learned_count, "active": current_active}

	movesets = getattr(pokemon, "movesets", None)
	if movesets is None:
		return {"learned": learned_count, "active": active_names}

	if hasattr(movesets, "get_or_create"):
		active_ms, _created = movesets.get_or_create(index=0)
	else:
		active_ms = None
		for candidate in _relation_items(movesets):
			if getattr(candidate, "index", None) == 0:
				active_ms = candidate
				break
		if active_ms is None and hasattr(movesets, "create"):
			active_ms = movesets.create(index=0)
	if active_ms is None:
		return {"learned": learned_count, "active": active_names}

	pokemon.active_moveset = active_ms
	_clear_moveset_slots(active_ms)
	for slot, move_name in enumerate(active_names, start=1):
		display_name = _move_display_name(move_name)
		if not display_name:
			continue
		move_obj, _created = Move.objects.get_or_create(name=display_name)
		active_ms.slots.create(move=move_obj, slot=slot)

	_save_pokemon(pokemon, update_fields=["active_moveset"])
	apply_active_moveset(pokemon)
	return {"learned": learned_count, "active": [_move_display_name(move) for move in active_names]}


def apply_current_pp(pokemon) -> int:
	"""Compute and apply ``current_pp`` for all active move slots.

	Returns the number of updated slots.
	"""

	movedex = _get_movedex()
	bonuses = getattr(pokemon, "pp_bonuses", {}) or {}
	if not bonuses:
		boosts = getattr(pokemon, "pp_boosts", None)
		if boosts is not None:
			try:
				iterable: Iterable = boosts.all()  # type: ignore[assignment]
			except Exception:
				iterable = boosts  # type: ignore[assignment]
			for boost in iterable:
				move_name = getattr(getattr(boost, "move", None), "name", "")
				if move_name:
					bonus = int(getattr(boost, "bonus_pp", 0) or 0)
					for key in {
						normalize_move_key(move_name),
						_fallback_normalize_key(move_name),
						str(move_name or "").lower(),
					}:
						if key:
							bonuses[key] = bonus

	slots = getattr(pokemon, "activemoveslot_set", None)
	if slots is None:
		return 0
	try:
		slot_iter = list(slots.all())
	except Exception:
		slot_iter = list(slots)

	updated = []
	for slot in slot_iter:
		move = getattr(slot, "move", None)
		if not move:
			continue
		move_name = getattr(move, "name", "") or str(move)
		norm = normalize_move_key(move_name)
		matched_key, base_pp = _get_move_pp_from_dex(movedex, move_name)
		if base_pp is None:
			continue
		bonus = bonuses.get(norm, 0)
		if not bonus and matched_key:
			bonus = bonuses.get(matched_key, 0)
		slot.current_pp = int(base_pp) + int(bonus or 0)
		updated.append(slot)

	if updated:
		try:
			slots.bulk_update(updated, ["current_pp"])
		except Exception:
			for slot in updated:
				try:
					slot.save()
				except Exception:
					pass
	return len(updated)


def learn_level_up_moves(pokemon, *, caller=None, prompt: bool = False) -> None:
	"""Teach all level-up moves available to ``pokemon``.

	Parameters
	----------
	pokemon:
	    The Pokémon instance gaining moves.
	caller:
	    Optional Evennia caller used when interactive prompts are desired.
	prompt:
	    If ``True`` and the underlying ``learn_move`` implementation supports
	    it, the player may be prompted to replace an existing move when the
	    active moveset is full.
	"""

	try:
		from pokemon.utils.move_learning import (
			get_learnable_levelup_moves,
			learn_move,
		)
	except ImportError:  # pragma: no cover - boundary: optional move-learning module
		return

	moves, _level_map = get_learnable_levelup_moves(pokemon)
	for mv in moves:
		try:
			learn_move(pokemon, mv, caller=caller, prompt=prompt)
		except (AttributeError, TypeError, ValueError):  # pragma: no cover - ignore malformed move rows
			logger.debug("Failed to teach move '%s' during level-up learning.", mv, exc_info=True)
			continue


def apply_active_moveset(pokemon) -> None:
	"""Populate ``pokemon``'s ``ActiveMoveslot`` records from its moveset.

	The operation is transactional to avoid partially-applied data and performs
	bulk creation for efficiency.  PP values are initialised from ``MOVEDEX``
	and adjusted for any stored PP bonuses.
	"""

	active_ms = getattr(pokemon, "active_moveset", None)
	if not active_ms:
		return

	slots_rel = getattr(active_ms, "slots", None)
	if slots_rel is None:
		return

	actives = getattr(pokemon, "activemoveslot_set", None)
	if actives is None:
		return

	pending = []
	SlotModel = getattr(actives, "model", None)

	def _apply():
		try:
			slot_iter = list(slots_rel.all().order_by("slot"))
		except AttributeError:
			try:
				slot_iter = list(slots_rel.order_by("slot"))
			except AttributeError:
				slot_iter = list(slots_rel)

		for slot in slot_iter:
			move = getattr(slot, "move", None)
			if not move:
				continue

			if SlotModel is not None:
				pending.append(
					SlotModel(
						pokemon=pokemon,
						move=move,
						slot=getattr(slot, "slot", 0),
						current_pp=None,
					)
				)
			else:
				actives.create(
					move=move,
					slot=getattr(slot, "slot", 0),
					current_pp=None,
				)

		if SlotModel is not None:
			actives.all().delete()
			if pending:
				try:
					actives.bulk_create(pending)
				except (AttributeError, TypeError):
					logger.debug("bulk_create unavailable; falling back to per-row create.", exc_info=True)
					for row in pending:
						actives.create(
							move=row.move,
							slot=row.slot,
							current_pp=row.current_pp,
						)
		apply_current_pp(pokemon)
		try:
			pokemon.save()
		except (AttributeError, TypeError):
			logger.debug("Unable to persist Pokémon after applying active moveset.", exc_info=True)

	try:
		with transaction.atomic():
			_apply()
	except (transaction.TransactionManagementError, ImproperlyConfigured):
		logger.debug("Transaction unavailable; applying active moveset without atomic block.", exc_info=True)
		_apply()


def backfill_owned_pokemon_movesets(
	*,
	queryset=None,
	dry_run: bool = True,
	replace_active: bool = False,
	limit: int | None = None,
) -> dict:
	"""Backfill learned moves and generated active movesets for owned PokÃ©mon."""

	if queryset is None:
		from pokemon.models.core import OwnedPokemon

		queryset = OwnedPokemon.objects.all()

	try:
		queryset = queryset.select_related("active_moveset").prefetch_related(
			"learned_moves",
			"movesets__slots__move",
			"activemoveslot_set__move",
		)
	except AttributeError:
		pass

	if limit is not None:
		queryset = queryset[: max(0, int(limit))]

	summary = {
		"checked": 0,
		"would_update": 0,
		"updated": 0,
		"skipped": 0,
		"errors": [],
	}

	try:
		iterator = queryset.iterator(chunk_size=100)
	except AttributeError:
		iterator = iter(queryset)

	for pokemon in iterator:
		summary["checked"] += 1
		try:
			level_moves = level_up_move_names_for_pokemon(pokemon)
			desired_active = default_active_move_names_for_pokemon(pokemon)
			learned_norms = _move_norms(_relation_items(getattr(pokemon, "learned_moves", None), order_by="name"))
			missing_learned = [
				move for move in level_moves if normalize_move_key(move) not in learned_norms
			]
			current_active = _active_moveset_slot_names(pokemon)
			should_replace_active = replace_active or not current_active
			active_changed = should_replace_active and _move_norms(current_active) != _move_norms(desired_active)
			needs_update = bool(missing_learned or active_changed)

			if not needs_update:
				summary["skipped"] += 1
				continue
			if dry_run:
				summary["would_update"] += 1
				continue

			initialize_generated_moveset(
				pokemon,
				active_move_names=desired_active,
				replace_active=should_replace_active,
			)
			summary["updated"] += 1
		except Exception as err:
			identifier = getattr(pokemon, "unique_id", getattr(pokemon, "id", "?"))
			summary["errors"].append(f"{identifier}: {err}")
			logger.warning("Failed to backfill moveset for %s", identifier, exc_info=True)

	return summary


__all__ = [
	"learn_level_up_moves",
	"initialize_generated_moveset",
	"level_up_move_names_for_pokemon",
	"default_active_move_names_for_pokemon",
	"backfill_owned_pokemon_movesets",
	"apply_active_moveset",
	"apply_current_pp",
	"normalize_move_key",
]
