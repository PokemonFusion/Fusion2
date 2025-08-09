from pokemon.utils.enhanced_evmenu import EnhancedEvMenu as EvMenu
from pokemon.generation import get_valid_moves
from pokemon.middleware import get_moveset_by_name
from pokemon.utils.move_learning import learn_move


def node_start(caller, raw_input=None, **kwargs):
    pokemon = kwargs.get("pokemon")
    moves = kwargs.get("moves")
    level_map = kwargs.get("level_map", {})
    if moves is None:
        known = {m.name.lower() for m in pokemon.learned_moves.all()}
        _, moveset = get_moveset_by_name(pokemon.species)
        if moveset:
            lvl_moves = [
                (lvl, mv)
                for lvl, mv in moveset["level-up"]
                if lvl <= pokemon.computed_level
            ]
            lvl_moves.sort(key=lambda x: x[0])
            ordered = [mv for _, mv in lvl_moves]
            level_map = {mv: lvl for lvl, mv in lvl_moves}
        else:
            ordered = get_valid_moves(pokemon.species, pokemon.computed_level)
            level_map = {}
        moves = [m for m in ordered if m.lower() not in known]
        if not moves:
            caller.msg(f"{pokemon.name} has no new moves to learn.")
            return None, None
        kwargs["moves"] = moves
        kwargs["level_map"] = level_map
    if raw_input is None:
        lines = [f"Choose a move for {pokemon.name} to learn:"]
        for mv in moves:
            lvl = level_map.get(mv)
            prefix = f"Lv{lvl} " if lvl is not None else ""
            lines.append(f"  {prefix}{mv.capitalize()}")
        lines.append("Type the move name, 'all' to learn all, or 'cancel' to quit.")
        return "\n".join(lines), [{"key": "_default", "goto": ("node_start", kwargs)}]
    cmd = raw_input.strip().lower()
    if cmd in {"cancel", "c", "q", "quit", "exit"}:
        return None, None
    if cmd == "all":
        def learn_next(idx=0):
            if idx >= len(moves):
                caller.msg(f"{pokemon.name} learned all available moves.")
                return
            mv = moves[idx]

            def _callback(*_args, **_kwargs):
                learn_next(idx + 1)

            learn_move(pokemon, mv, caller=caller, prompt=True, on_exit=_callback)

        learn_next()
        return None, None
    for mv in moves:
        if mv.lower() == cmd:
            learn_move(pokemon, mv, caller=caller, prompt=True)
            return f"{pokemon.name} learned {mv.capitalize()}.", None
    caller.msg("Invalid choice.")
    return node_start(caller, **kwargs)
