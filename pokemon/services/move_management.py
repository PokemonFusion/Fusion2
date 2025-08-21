"""Service functions for managing Pokémon moves.

The project historically stored a fair amount of move related logic on the
``OwnedPokemon`` model.  To keep that model lean and more easily testable,
the behaviour has been moved into this module.  The model now exposes thin
wrappers that delegate to these helpers.
"""

from __future__ import annotations

from typing import Iterable

from django.db import transaction


def _fallback_normalize_key(val: str) -> str:
	"""Simplified move name normalisation used when engine helpers are
	missing."""

	return val.replace(" ", "").replace("-", "").replace("'", "").lower()


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
	except Exception:  # pragma: no cover - module may be unavailable in tests
		return

	moves, _level_map = get_learnable_levelup_moves(pokemon)
	for mv in moves:
		try:
			learn_move(pokemon, mv, caller=caller, prompt=prompt)
		except Exception:  # pragma: no cover - ignore problematic moves
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

	try:
		from pokemon.battle.engine import _normalize_key
	except Exception:
		_normalize_key = _fallback_normalize_key

	import sys

	dex_mod = sys.modules.get("pokemon.dex")
	if dex_mod is None:
		try:
			from pokemon import dex as dex_mod  # type: ignore
		except Exception:
			dex_mod = None

	bonuses = getattr(pokemon, "pp_bonuses", {}) or {}
	if not bonuses:
		boosts = getattr(pokemon, "pp_boosts", None)
		if boosts is not None:
			try:
				iterable: Iterable = boosts.all()  # type: ignore[assignment]
			except Exception:
				iterable = boosts  # type: ignore[assignment]
			for b in iterable:
				name = getattr(getattr(b, "move", None), "name", "")
				if name:
					bonuses[_normalize_key(name)] = getattr(b, "bonus_pp", 0)
	pending = []
	SlotModel = getattr(actives, "model", None)

	def _apply():
		try:
			slot_iter = list(slots_rel.all().order_by("slot"))
		except Exception:
			try:
				slot_iter = list(slots_rel.order_by("slot"))
			except Exception:
				slot_iter = list(slots_rel)

		for slot in slot_iter:
			move = getattr(slot, "move", None)
			if not move:
				continue
			name = getattr(move, "name", "") or str(move)
			norm = _normalize_key(name)

			base_pp = None
			if dex_mod is not None:
				md = dex_mod.MOVEDEX.get(norm)
				if md is not None:
					base_pp = getattr(md, "pp", None)
					if base_pp is None and isinstance(md, dict):
						base_pp = md.get("pp")
			cur_pp = None if base_pp is None else int(base_pp) + int(bonuses.get(norm, 0))

			if SlotModel is not None:
				pending.append(
					SlotModel(
						move=move,
						slot=getattr(slot, "slot", 0),
						current_pp=cur_pp,
					)
				)
			else:
				actives.create(
					move=move,
					slot=getattr(slot, "slot", 0),
					current_pp=cur_pp,
				)

		if SlotModel is not None:
			actives.all().delete()
			if pending:
				try:
					actives.bulk_create(pending)
				except Exception:
					for row in pending:
						actives.create(
							move=row.move,
							slot=row.slot,
							current_pp=row.current_pp,
						)
		try:
			pokemon.save()
		except Exception:
			pass

	try:
		with transaction.atomic():
			_apply()
	except Exception:
		_apply()


__all__ = ["learn_level_up_moves", "apply_active_moveset"]
