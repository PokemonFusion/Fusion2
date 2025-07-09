from evennia.utils.evmenu import EvMenu


def node_start(caller, raw_input=None):
    """Select a Pokémon to manage."""
    if not (caller.location and caller.location.db.is_pokemon_center):
        caller.msg("You must be at a Pokémon Center to manage movesets.")
        return None, None
    mons = caller.storage.get_party() if hasattr(caller.storage, "get_party") else list(caller.storage.active_pokemon.all())
    if not mons:
        caller.msg("You have no active Pokémon.")
        return None, None
    if not raw_input:
        lines = ["|wSelect a Pokémon to manage|n"]
        for i, mon in enumerate(mons, 1):
            lines.append(f"  {i}. {mon.nickname} ({mon.name})")
        lines.append("Enter number or 'quit'.")
        return "\n".join(lines), [{"key": "_default", "goto": "node_start"}]
    if raw_input.strip().lower() == "quit":
        return "Exiting Moveset Manager.", None
    try:
        idx = int(raw_input.strip()) - 1
        pokemon = mons[idx]
    except (ValueError, IndexError):
        caller.msg("Invalid choice.")
        return "node_start", {}
    caller.ndb.ms_pokemon = pokemon
    return node_manage(caller)


def node_manage(caller, raw_input=None):
    poke = caller.ndb.ms_pokemon
    sets = poke.movesets or []
    while len(sets) < 4:
        sets.append([])
    if raw_input is None:
        lines = [f"|wManaging movesets for {poke.nickname} ({poke.name})|n"]
        for i, s in enumerate(sets, 1):
            marker = "*" if i - 1 == poke.active_moveset else " "
            moves = ", ".join(s) if s else "(empty)"
            lines.append(f"{marker}{i}. {moves}")
        lines.append("Commands: swap <n>, edit <n>, back")
        return "\n".join(lines), [{"key": "_default", "goto": "node_manage"}]
    cmd = raw_input.strip().lower()
    if cmd == "back":
        del caller.ndb.ms_pokemon
        return node_start(caller)
    parts = cmd.split(maxsplit=1)
    if len(parts) != 2:
        caller.msg("Invalid command.")
        return "node_manage", {}
    action, num = parts
    try:
        idx = int(num) - 1
    except ValueError:
        caller.msg("Invalid number.")
        return "node_manage", {}
    if idx < 0 or idx >= 4:
        caller.msg("Number must be 1-4.")
        return "node_manage", {}
    if action == "swap":
        poke.swap_moveset(idx)
        caller.msg(f"Active moveset set to {idx+1}.")
        return "node_manage", {}
    if action == "edit":
        caller.ndb.ms_index = idx
        return "node_edit", {}
    caller.msg("Unknown command.")
    return "node_manage", {}


def node_edit(caller, raw_input=None):
    poke = caller.ndb.ms_pokemon
    idx = caller.ndb.ms_index
    sets = poke.movesets or []
    while len(sets) < 4:
        sets.append([])
    if raw_input is None:
        current = ", ".join(sets[idx]) if sets[idx] else "(empty)"
        text = f"Enter up to 4 moves for set {idx+1} separated by commas [current: {current}]:"
        return text, [{"key": "_default", "goto": "node_edit"}]
    moves = [m.strip() for m in raw_input.split(',') if m.strip()][:4]
    sets[idx] = moves
    poke.movesets = sets
    if idx == poke.active_moveset:
        poke.moves = moves
    poke.save()
    caller.msg(f"Moveset {idx+1} updated.")
    return node_manage(caller)

