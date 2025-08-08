"""Service functions for managing Pokémon moves.

The project historically stored a fair amount of move related logic on the
``OwnedPokemon`` model.  To keep that model lean and more easily testable,
the behaviour has been moved into this module.  The model now exposes thin
wrappers that delegate to these helpers.
"""

from __future__ import annotations

from typing import Iterable, Optional


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
    """Populate active move slots for ``pokemon``'s current moveset.

    This mirrors the Pokémon's active moveset to the ``ActiveMoveslot`` table
    used during battles.  Existing slots are cleared and recreated so that the
    database always reflects the active configuration.  ``current_pp`` values
    are initialised based on the move's base PP along with any stored PP
    boosts.
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

    # clear existing active slots
    try:
        actives.all().delete()
    except Exception:  # pragma: no cover - non-queryset fallbacks
        try:
            actives.delete()
        except Exception:
            try:
                for obj in list(actives):
                    try:
                        obj.delete()
                    except Exception:
                        pass
                actives.clear()  # type: ignore[attr-defined]
            except Exception:
                pass

    # determine PP bonuses from PP Ups / PP Maxes
    bonuses: dict[str, int] = {}
    boosts = getattr(pokemon, "pp_boosts", None)
    if boosts is not None:
        try:
            iterable: Iterable = boosts.all()
        except Exception:  # pragma: no cover - manager may be list-like
            iterable = boosts  # type: ignore[assignment]
        for b in iterable:
            name = getattr(getattr(b, "move", None), "name", "").lower()
            if name:
                bonuses[name] = getattr(b, "bonus_pp", 0)

    try:
        slot_iter = slots_rel.order_by("slot")
    except Exception:  # pragma: no cover - list-like fallback
        slot_iter = slots_rel

    try:
        from pokemon.dex import MOVEDEX  # type: ignore
    except Exception:  # pragma: no cover - optional during some tests
        MOVEDEX = {}  # type: ignore

    for slot in slot_iter:
        move = getattr(slot, "move", None)
        if not move:
            continue
        move_name = getattr(move, "name", "").lower()
        pp: Optional[int] = None
        base_pp = MOVEDEX.get(move_name, {}).get("pp")
        if base_pp is not None:
            pp = base_pp + bonuses.get(move_name, 0)
        try:
            actives.create(move=move, slot=getattr(slot, "slot", 0), current_pp=pp)
        except Exception:  # pragma: no cover - best effort
            pass

    try:
        pokemon.save()
    except Exception:  # pragma: no cover - optional in tests
        pass


__all__ = ["learn_level_up_moves", "apply_active_moveset"]

