from pokemon.utils.enhanced_evmenu import EnhancedEvMenu as EvMenu
from pokemon.generation import get_valid_moves
from pokemon.utils.move_learning import learn_move


def node_start(caller, raw_input=None, **kwargs):
    pokemon = kwargs.get("pokemon")
    moves = kwargs.get("moves")
    if moves is None:
        known = {m.name.lower() for m in pokemon.learned_moves.all()}
        moves = [m for m in get_valid_moves(pokemon.species, pokemon.level) if m.lower() not in known]
        if not moves:
            caller.msg(f"{pokemon.name} has no new moves to learn.")
            return None, None
        kwargs["moves"] = moves
    if raw_input is None:
        lines = [f"Choose a move for {pokemon.name} to learn:"]
        for mv in moves:
            lines.append(f"  {mv.capitalize()}")
        lines.append("Type the move name, 'all' to learn all, or 'cancel' to quit.")
        return "\n".join(lines), [{"key": "_default", "goto": ("node_start", kwargs)}]
    cmd = raw_input.strip().lower()
    if cmd in {"cancel", "c", "q", "quit", "exit"}:
        return None, None
    if cmd == "all":
        for mv in moves:
            learn_move(pokemon, mv, caller=caller, prompt=True)
        return f"{pokemon.name} learned all available moves.", None
    for mv in moves:
        if mv.lower() == cmd:
            learn_move(pokemon, mv, caller=caller, prompt=True)
            return f"{pokemon.name} learned {mv.capitalize()}.", None
    caller.msg("Invalid choice.")
    return node_start(caller, **kwargs)
