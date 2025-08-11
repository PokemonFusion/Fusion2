from helpers.enhanced_evmenu import EnhancedEvMenu as EvMenu, free_input_node
from evennia import create_object
from typeclasses.rooms import Room
from typeclasses.exits import Exit


def _list_rooms(caller):
    lines = [f"{room.id} - {room.key}" for room in Room.objects.all()]
    caller.msg("\n".join(lines))


@free_input_node
def node_start(caller, raw_input=None):
    """Select room to edit."""
    if not raw_input:
        text = "Enter room ID to edit or type 'list rooms':"
        return text, {"goto": "node_start"}
    cmd = raw_input.strip()
    if cmd.lower().startswith("list"):
        _list_rooms(caller)
        return "Enter room ID:", {"goto": "node_start"}
    try:
        rid = int(cmd.strip("#"))
        room = Room.objects.get(id=rid)
    except (ValueError, Room.DoesNotExist):
        caller.msg("Invalid room ID.")
        return "Enter room ID:", {"goto": "node_start"}
    caller.ndb.er_room = room
    caller.ndb.er_data = {
        "name": room.key,
        "desc": room.db.desc or "",
        "is_center": room.db.is_pokemon_center,
        "is_shop": room.db.is_item_shop,
        "allow_hunting": room.db.allow_hunting,
        "hunt_chart": room.db.hunt_chart or [],
    }
    return node_name(caller)


@free_input_node
def node_name(caller, raw_input=None):
    data = caller.ndb.er_data
    if raw_input is None:
        text = f"Current name: {data['name']}. Enter new name or leave blank:"
        return text, {"goto": "node_name"}
    if raw_input.strip():
        data['name'] = raw_input.strip()
    text = "Enter new description or leave blank to keep current:"
    return text, {"goto": "node_desc"}


@free_input_node
def node_desc(caller, raw_input):
    data = caller.ndb.er_data
    if raw_input is None:
        text = "Enter new description or leave blank:"
        return text, {"goto": "node_desc"}
    if raw_input.strip():
        data['desc'] = raw_input
    text = f"Is this a Pokémon Center? (yes/no) [current: {'yes' if data.get('is_center') else 'no'}]"
    return text, [
        {"key": "yes", "goto": "node_center_yes"},
        {"key": "no", "goto": "node_center_no"},
    ]


def node_center_yes(caller, raw_input=None):
    caller.ndb.er_data['is_center'] = True
    text = f"Is this an Item Shop? (yes/no) [current: {'yes' if caller.ndb.er_data.get('is_shop') else 'no'}]"
    return text, [
        {"key": "yes", "goto": "node_shop_yes"},
        {"key": "no", "goto": "node_shop_no"},
    ]


def node_center_no(caller, raw_input=None):
    caller.ndb.er_data['is_center'] = False
    text = f"Is this an Item Shop? (yes/no) [current: {'yes' if caller.ndb.er_data.get('is_shop') else 'no'}]"
    return text, [
        {"key": "yes", "goto": "node_shop_yes"},
        {"key": "no", "goto": "node_shop_no"},
    ]


def node_shop_yes(caller, raw_input=None):
    caller.ndb.er_data['is_shop'] = True
    text = f"Allow Pokémon hunting? (yes/no) [current: {'yes' if caller.ndb.er_data.get('allow_hunting') else 'no'}]"
    return text, [
        {"key": "yes", "goto": "node_hunt_yes"},
        {"key": "no", "goto": "node_hunt_no"},
    ]


def node_shop_no(caller, raw_input=None):
    caller.ndb.er_data['is_shop'] = False
    text = f"Allow Pokémon hunting? (yes/no) [current: {'yes' if caller.ndb.er_data.get('allow_hunting') else 'no'}]"
    return text, [
        {"key": "yes", "goto": "node_hunt_yes"},
        {"key": "no", "goto": "node_hunt_no"},
    ]


@free_input_node
def node_hunt_yes(caller, raw_input=None):
    caller.ndb.er_data['allow_hunting'] = True
    return "Enter encounter table as name:rate, name:rate or blank to keep:", {"goto": "node_hunt_table"}


def node_hunt_no(caller, raw_input=None):
    caller.ndb.er_data['allow_hunting'] = False
    return node_summary(caller)


@free_input_node
def node_hunt_table(caller, raw_input):
    data = caller.ndb.er_data
    if not raw_input.strip():
        return node_summary(caller)
    table = {}
    for entry in raw_input.split(','):
        try:
            mon, rate = entry.split(':')
            table[mon.strip()] = int(rate.strip())
        except ValueError:
            caller.msg("Invalid format. Use name:rate, name:rate")
            return "Enter encounter table as name:rate, name:rate:", {"goto": "node_hunt_table"}
    data['hunt_chart'] = [
        {"name": mon.strip(), "weight": int(rate.strip())}
        for mon, rate in table.items()
    ]
    return node_summary(caller)


def node_summary(caller, raw_input=None):
    data = caller.ndb.er_data
    text = (
        "|gRoom Edit Summary|n\n"
        f"Name:        {data['name']}\n"
        f"Description: {data['desc']}\n"
        f"Center:      {'Yes' if data.get('is_center') else 'No'}\n"
        f"Shop:        {'Yes' if data.get('is_shop') else 'No'}\n"
        f"Hunting:     {'Yes' if data.get('allow_hunting') else 'No'}\n"
    )
    if data.get("allow_hunting"):
        for entry in data.get("hunt_chart", []):
            text += f"  - {entry['name']}: {entry.get('weight', 1)}%\n"
    text += "\nType |wsave|n to apply changes or |wquit|n to abort."
    return text, [
        {"key": "save", "goto": "node_save"},
        {"key": "quit", "goto": "node_quit"},
    ]


def node_save(caller, raw_input=None):
    room = caller.ndb.er_room
    data = caller.ndb.er_data
    room.key = data['name']
    room.db.desc = data['desc']
    room.db.is_pokemon_center = data.get('is_center', False)
    room.db.is_item_shop = data.get('is_shop', False)
    room.db.allow_hunting = data.get('allow_hunting', False)
    room.db.hunt_chart = data.get('hunt_chart', [])
    caller.msg(f"|gRoom '{room.key}' updated.|n")
    caller.ndb.rw_room = room
    del caller.ndb.er_data
    del caller.ndb.er_room
    return (
        "Would you like to add exits to this room? (yes/no)",
        [
            {"key": "yes", "goto": "node_exit_dir"},
            {"key": "no", "goto": "node_quit"},
        ],
    )


@free_input_node
def node_exit_dir(caller, raw_input=None):
    room = caller.ndb.rw_room
    if not raw_input:
        text = (
            "Enter exit as <direction>=<room_id> or 'list rooms'.\n"
            "Type 'done' when finished."
        )
        return text, {"goto": "node_exit_dir"}
    cmd = raw_input.strip()
    if cmd.lower().startswith("list"):
        _list_rooms(caller)
        return "Enter exit as <dir>=<id> or 'done':", {"goto": "node_exit_dir"}
    if cmd.lower() == "done":
        return node_quit(caller)
    if "=" not in cmd:
        caller.msg("Usage: <direction>=<room_id> or 'done'.")
        return "Enter exit as <dir>=<id> or 'done':", {"goto": "node_exit_dir"}
    direction, rid = [s.strip() for s in cmd.split("=", 1)]
    try:
        dest = Room.objects.get(id=int(rid))
    except (ValueError, Room.DoesNotExist):
        caller.msg("Invalid room id.")
        return "Enter exit as <dir>=<id> or 'done':", {"goto": "node_exit_dir"}
    create_object(Exit, key=direction, location=room, destination=dest)
    caller.msg(f"Created exit '{direction}' to {dest.key}.")
    return "Add another exit or 'done' when finished:", {"goto": "node_exit_dir"}


def node_quit(caller, raw_input=None):
    if hasattr(caller.ndb, "rw_room"):
        del caller.ndb.rw_room
    if hasattr(caller.ndb, "er_data"):
        del caller.ndb.er_data
    if hasattr(caller.ndb, "er_room"):
        del caller.ndb.er_room
    return "Exiting Room Editor. Thanks!", None
