from __future__ import annotations

from pokemon.names import find_named, normalize_name
from pokemon.services.move_management import apply_active_moveset


def get_learnable_levelup_moves(pokemon):
	"""Return a list of level-up moves the Pokémon can still learn.

	Returns a tuple ``(moves, level_map)`` where ``moves`` is an ordered list
	of move names and ``level_map`` maps each move to the level it is learned
	at (if available).
	"""

	from pokemon.data.generation import get_valid_moves
	from pokemon.middleware import get_moveset_by_name

	known = {normalize_name(m.name) for m in pokemon.learned_moves.all()}
	_, moveset = get_moveset_by_name(pokemon.species)
	if moveset:
		lvl_moves = [
			(lvl, mv) for lvl, mv in moveset["level-up"] if lvl <= pokemon.computed_level and normalize_name(mv) not in known
		]
		lvl_moves.sort(key=lambda x: x[0])
		moves = [mv for lvl, mv in lvl_moves]
		level_map = {mv: lvl for lvl, mv in lvl_moves}
	else:
		moves = [mv for mv in get_valid_moves(pokemon.species, pokemon.computed_level) if normalize_name(mv) not in known]
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

	from pokemon.services.move_management import get_or_create_move

	move_obj = get_or_create_move(move_name, pokemon=pokemon)
	learned = pokemon.learned_moves
	if find_named(learned.all() if hasattr(learned, "all") else learned, move_name) is None:
		pokemon.learned_moves.add(move_obj)

	# ensure moveset structure exists
	if not pokemon.movesets.exists():
		ms = pokemon.movesets.create(index=0)
		pokemon.active_moveset = ms
		pokemon.save()
	active_ms = pokemon.active_moveset or pokemon.movesets.order_by("index").first()
	active = [s.move.name for s in active_ms.slots.order_by("slot")] if active_ms else []
	if find_named(active, move_name) is not None:
		if on_exit:
			on_exit(caller, None)
		return

	# if there's space, add automatically
	if len(active) < 4:
		active_ms.slots.create(move=move_obj, slot=len(active) + 1)
		pokemon.save()
		apply_active_moveset(pokemon)
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
	from utils.enhanced_evmenu import EnhancedEvMenu

	EnhancedEvMenu(
		caller,
		learn_menu,
		startnode="node_start",
		start_kwargs={"pokemon": pokemon, "move_name": move_name},
		cmd_on_exit=on_exit,
	)
