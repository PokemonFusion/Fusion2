from utils.enhanced_evmenu import EnhancedEvMenu as EvMenu


def _get_boxes(caller):
    storage = caller.storage
    return list(storage.boxes.all().order_by("id"))


def _get_party(caller):
    storage = caller.storage
    if hasattr(storage, "get_party"):
        return storage.get_party()
    return list(storage.active_pokemon.all())


def node_start(caller, raw_input=None, **kwargs):
    boxes = _get_boxes(caller)
    if raw_input is None:
        lines = ["|wPokémon Storage|n"]
        for i, box in enumerate(boxes, 1):
            lines.append(f"  {i}. {box.name} ({box.pokemon.count()})")
        lines.append("D. Deposit from party")
        lines.append("Q. Quit")
        return "\n".join(lines), [{"key": "_default", "goto": "node_start"}]

    cmd = raw_input.strip().lower()
    if cmd in {"q", "quit", "exit"}:
        return "Exiting storage.", None
    if cmd == "d":
        return node_deposit(caller)
    if cmd.isdigit():
        idx = int(cmd) - 1
        if 0 <= idx < len(boxes):
            kwargs["box_index"] = idx
            return node_box(caller, **kwargs)
    caller.msg("Invalid choice.")
    return node_start(caller, **kwargs)


def node_box(caller, raw_input=None, **kwargs):
    boxes = _get_boxes(caller)
    idx = kwargs.get("box_index", 0)
    box = boxes[idx]
    mons = list(box.pokemon.all())
    if raw_input is None:
        lines = [f"|w{box.name}|n"]
        for i, mon in enumerate(mons, 1):
            disp = mon.nickname or mon.species
            lines.append(f"  {i}. {disp}")
        lines.append("B. Back")
        return "\n".join(lines), [{"key": "_default", "goto": "node_box"}]

    cmd = raw_input.strip().lower()
    if cmd == "b":
        return node_start(caller)
    if cmd.isdigit():
        i = int(cmd) - 1
        if 0 <= i < len(mons):
            mon = mons[i]
            caller.msg(caller.withdraw_pokemon(mon.unique_id, idx + 1))
            return node_box(caller, **kwargs)
    caller.msg("Invalid choice.")
    return node_box(caller, **kwargs)


def node_deposit(caller, raw_input=None, **kwargs):
    party = _get_party(caller)
    if raw_input is None:
        lines = ["Select a Pokémon to deposit:"]
        for i, mon in enumerate(party, 1):
            disp = mon.nickname or mon.species
            lines.append(f"  {i}. {disp}")
        lines.append("B. Back")
        return "\n".join(lines), [{"key": "_default", "goto": "node_deposit"}]

    cmd = raw_input.strip().lower()
    if cmd == "b":
        return node_start(caller)
    if cmd.isdigit():
        i = int(cmd) - 1
        if 0 <= i < len(party):
            kwargs["poke_id"] = party[i].unique_id
            return node_choose_box(caller, **kwargs)
    caller.msg("Invalid choice.")
    return node_deposit(caller, **kwargs)


def node_choose_box(caller, raw_input=None, **kwargs):
    boxes = _get_boxes(caller)
    if raw_input is None:
        lines = ["Deposit into which box?"]
        for i, box in enumerate(boxes, 1):
            lines.append(f"  {i}. {box.name}")
        lines.append("B. Back")
        return "\n".join(lines), [{"key": "_default", "goto": "node_choose_box"}]

    cmd = raw_input.strip().lower()
    if cmd == "b":
        return node_deposit(caller)
    if cmd.isdigit():
        i = int(cmd) - 1
        if 0 <= i < len(boxes):
            pid = kwargs.get("poke_id")
            caller.msg(caller.deposit_pokemon(pid, i + 1))
            return node_start(caller)
    caller.msg("Invalid choice.")
    return node_choose_box(caller, **kwargs)

