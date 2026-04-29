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


__all__ = [
	"learn_level_up_moves",
	"apply_active_moveset",
	"apply_current_pp",
	"normalize_move_key",
]
