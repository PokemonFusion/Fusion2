from __future__ import annotations

from typing import Optional

from pokemon.utils.enhanced_evmenu import EnhancedEvMenu
from pokemon.models import Move


def learn_move(pokemon, move_name: str, *, caller=None, prompt: bool = False) -> None:
    """Teach ``move_name`` to ``pokemon``.

    If ``prompt`` is True and ``caller`` is provided, the caller will be asked
    whether to replace one of the Pokémon's active moves with the new move when
    the active moveset is already full. The move is always added to the learned
    moves list first.
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
        return

    pokemon.save()
    if not (prompt and caller):
        if caller:
            caller.msg(f"{pokemon.name} learned {move_name.capitalize()} (stored).")
        return

    from menus import learn_move as learn_menu

    EnhancedEvMenu(
        caller,
        learn_menu,
        startnode="node_start",
        kwargs={"pokemon": pokemon, "move_name": move_name},
        cmd_on_exit=None,
    )
