from pokemon.utils.enhanced_evmenu import EnhancedEvMenu as EvMenu
from pokemon.models.moves import Move
from pokemon.services.move_management import apply_active_moveset


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
    ms = getattr(pokemon, "active_moveset", None)
    moves = [s.move.name for s in ms.slots.order_by("slot")] if ms else []
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
    ms = getattr(pokemon, "active_moveset", None)
    if not ms:
        return node_done(caller, **kwargs)
    slots = list(ms.slots.order_by("slot"))
    if slot < 0 or slot >= len(slots):
        caller.msg("Invalid choice.")
        return node_choose(caller, **kwargs)
    old = slots[slot].move.name
    move_obj, _ = Move.objects.get_or_create(name=move_name.capitalize())
    slots[slot].move = move_obj
    slots[slot].save()
    apply_active_moveset(pokemon)
    return f"{pokemon.name} forgot {old.capitalize()} and learned {move_name.capitalize()}!", None


def node_done(caller, raw_input=None, **kwargs):
    pokemon = kwargs.get("pokemon")
    move_name = kwargs.get("move_name", "")
    return f"{pokemon.name} learned {move_name.capitalize()}.", None
