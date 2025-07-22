from __future__ import annotations

from typing import Optional

from pokemon.utils.enhanced_evmenu import EnhancedEvMenu
from pokemon.models import Move


def get_learnable_levelup_moves(pokemon):
    """Return a list of level-up moves the Pokémon can still learn.

    Returns a tuple ``(moves, level_map)`` where ``moves`` is an ordered list
    of move names and ``level_map`` maps each move to the level it is learned
    at (if available).
    """

    from pokemon.generation import get_valid_moves
    from pokemon.middleware import get_moveset_by_name

    known = {m.name.lower() for m in pokemon.learned_moves.all()}
    _, moveset = get_moveset_by_name(pokemon.species)
    if moveset:
        lvl_moves = [
            (lvl, mv)
            for lvl, mv in moveset["level-up"]
            if lvl <= pokemon.computed_level and mv.lower() not in known
        ]
        lvl_moves.sort(key=lambda x: x[0])
        moves = [mv for lvl, mv in lvl_moves]
        level_map = {mv: lvl for lvl, mv in lvl_moves}
    else:
        moves = [
            mv
            for mv in get_valid_moves(pokemon.species, pokemon.computed_level)
            if mv.lower() not in known
        ]
        level_map = {}

    return moves, level_map


def learn_move(pokemon, move_name: str, *, caller=None, prompt: bool = False, on_exit=None) -> None:
    """Teach ``move_name`` to ``pokemon``.

    If ``prompt`` is True and ``caller`` is provided, the caller will be asked
    whether to replace one of the Pokémon's active moves with the new move when
    the active moveset is already full. The move is always added to the learned
    moves list first. If ``on_exit`` is given, it will be called with
    ``(caller, menu)`` when any interactive prompt menu closes.
    """

    if not pokemon or not move_name:
        return

    move_obj, _ = Move.objects.get_or_create(name=move_name.capitalize())
    if not pokemon.learned_moves.filter(name__iexact=move_name).exists():
        pokemon.learned_moves.add(move_obj)

    # ensure movesets structure exists
    sets = pokemon.movesets or [[]]
    if not sets:
        sets = [[]]
    active_idx = pokemon.active_moveset_index if pokemon.active_moveset_index < len(sets) else 0
    active = sets[active_idx]

    # if there's space, add automatically
    if len(active) < 4 and move_name not in active:
        active.append(move_name)
        pokemon.movesets = sets
        pokemon.save()
        pokemon.apply_active_moveset()
        if caller:
            caller.msg(f"{pokemon.name} learned {move_name.capitalize()}!")
        if on_exit:
            on_exit(caller, None)
        return

    pokemon.save()
    if not (prompt and caller):
        if caller:
            caller.msg(f"{pokemon.name} learned {move_name.capitalize()} (stored).")
        if on_exit:
            on_exit(caller, None)
        return

    from menus import learn_move as learn_menu

    EnhancedEvMenu(
        caller,
        learn_menu,
        startnode="node_start",
        kwargs={"pokemon": pokemon, "move_name": move_name},
        cmd_on_exit=on_exit,
    )
