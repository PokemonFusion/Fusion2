from pokemon.utils.enhanced_evmenu import EnhancedEvMenu as EvMenu


def node_start(caller, raw_input=None, **kwargs):
    pokemon = kwargs.get("pokemon")
    move_name = kwargs.get("move_name", "").capitalize()
    text = f"{pokemon.name} learned {move_name}! Replace an active move with it? (yes/no)"
    return text, [
        {"key": "yes", "goto": ("node_choose", kwargs)},
        {"key": "no", "goto": ("node_done", kwargs)},
    ]


def node_choose(caller, raw_input=None, **kwargs):
    pokemon = kwargs.get("pokemon")
    move_name = kwargs.get("move_name", "").capitalize()
    idx = pokemon.active_moveset_index if pokemon.active_moveset_index < len(pokemon.movesets or []) else 0
    moves = (pokemon.movesets or [[]])[idx]
    text = f"Which move should be replaced with {move_name}?"
    options = []
    for i, mv in enumerate(moves[:4], 1):
        options.append({"key": str(i), "desc": mv.capitalize(), "goto": ("node_replace", {**kwargs, "slot": i - 1})})
    options.append({"key": "cancel", "goto": ("node_done", kwargs)})
    return text, options


def node_replace(caller, raw_input=None, **kwargs):
    pokemon = kwargs.get("pokemon")
    move_name = kwargs.get("move_name")
    slot = kwargs.get("slot", 0)
    sets = pokemon.movesets or [[]]
    idx = pokemon.active_moveset_index if pokemon.active_moveset_index < len(sets) else 0
    moves = sets[idx]
    if slot < 0 or slot >= len(moves):
        caller.msg("Invalid choice.")
        return node_choose(caller, **kwargs)
    old = moves[slot]
    moves[slot] = move_name
    pokemon.movesets = sets
    pokemon.save()
    pokemon.apply_active_moveset()
    return f"{pokemon.name} forgot {old.capitalize()} and learned {move_name.capitalize()}!", None


def node_done(caller, raw_input=None, **kwargs):
    pokemon = kwargs.get("pokemon")
    move_name = kwargs.get("move_name", "")
    return f"{pokemon.name} learned {move_name.capitalize()}.", None
