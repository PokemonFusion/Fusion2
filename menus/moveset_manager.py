from pokemon.utils.enhanced_evmenu import EnhancedEvMenu as EvMenu
from pokemon.services.move_management import apply_active_moveset


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
            disp = mon.nickname or mon.species
            lines.append(f"  {i}. {disp}")
        lines.append("Enter number or 'quit'.")
        return "\n".join(lines), [{"key": "_default", "goto": "node_start"}]
    if raw_input.strip().lower() == "quit":
        return "Exiting Moveset Manager.", None
    try:
        idx = int(raw_input.strip()) - 1
        pokemon = mons[idx]
    except (ValueError, IndexError):
        caller.msg("Invalid choice.")
        return node_start(caller)
    caller.ndb.ms_pokemon = pokemon
    return node_manage(caller)


def node_manage(caller, raw_input=None):
    poke = caller.ndb.ms_pokemon
    sets = []
    for ms in poke.movesets.order_by("index"):
        sets.append([s.move.name for s in ms.slots.order_by("slot")])
    while len(sets) < 4:
        sets.append([])
    if raw_input is None:
        disp = poke.nickname or poke.species
        lines = [f"|wManaging movesets for {disp}|n"]
        active_idx = poke.active_moveset.index if poke.active_moveset else -1
        for i, s in enumerate(sets, 1):
            marker = "*" if i - 1 == active_idx else " "
            moves = ", ".join(s) if s else "(empty)"
            lines.append(f"{marker}{i}. {moves}")
        lines.append("Enter a number to edit that set, or type 'swap <n>' to make it active. Type 'back' or 'b' to exit.")
        return "\n".join(lines), [{"key": "_default", "goto": "node_manage"}]
    cmd = raw_input.strip().lower()
    if cmd in ("back", "b"):
        del caller.ndb.ms_pokemon
        return node_start(caller)
    if cmd.isdigit():
        idx = int(cmd) - 1
        if 0 <= idx < 4:
            caller.ndb.ms_index = idx
            return node_edit(caller)
        caller.msg("Number must be 1-4.")
        return node_manage(caller)
    parts = cmd.split(maxsplit=1)
    if len(parts) != 2:
        caller.msg("Invalid command.")
        return node_manage(caller)
    action, num = parts
    try:
        idx = int(num) - 1
    except ValueError:
        caller.msg("Invalid number.")
        return node_manage(caller)
    if idx < 0 or idx >= 4:
        caller.msg("Number must be 1-4.")
        return node_manage(caller)
    if action == "swap":
        poke.swap_moveset(idx)
        caller.msg(f"Active moveset set to {idx+1}.")
        return node_manage(caller)
    if action == "edit":
        caller.ndb.ms_index = idx
        return node_edit(caller)
    caller.msg("Unknown command.")
    return node_manage(caller)


def node_edit(caller, raw_input=None):
    poke = caller.ndb.ms_pokemon
    idx = caller.ndb.ms_index
    sets = {ms.index: ms for ms in poke.movesets.all()}
    if raw_input is None:
        current = ", ".join(
            [s.move.name for s in sets.get(idx).slots.order_by("slot")] if idx in sets else []
        ) or "(empty)"
        learned = [m.name for m in poke.learned_moves.all().order_by("name")]
        move_list = ", ".join(learned) if learned else "(none)"
        lines = [
            f"Available moves: {move_list}",
            f"Enter up to 4 moves for set {idx+1} separated by commas [current: {current}] (type 'back' or 'b' to cancel):",
        ]
        return "\n".join(lines), [{"key": "_default", "goto": "node_edit"}]
    cmd = raw_input.strip().lower()
    if cmd in ("back", "b"):
        return node_manage(caller)
    moves = [m.strip() for m in raw_input.split(',') if m.strip()][:4]
    learned = {m.name.lower() for m in poke.learned_moves.all().order_by("name")}
    invalid = [m for m in moves if m.lower() not in learned]
    if invalid:
        caller.msg("Invalid move(s): " + ", ".join(invalid))
        return node_edit(caller)
    if len({m.lower() for m in moves}) != len(moves):
        caller.msg("Duplicate moves are not allowed.")
        return node_edit(caller)
    from pokemon.models.moves import Move as MoveModel
    ms, _ = poke.movesets.get_or_create(index=idx)
    ms.slots.all().delete()
    for i, mv in enumerate(moves, 1):
        obj, _ = MoveModel.objects.get_or_create(name=mv.capitalize())
        ms.slots.create(move=obj, slot=i)
    if poke.active_moveset and poke.active_moveset.index == idx:
        apply_active_moveset(poke)
    caller.msg(f"Moveset {idx+1} updated.")
    return node_manage(caller)

