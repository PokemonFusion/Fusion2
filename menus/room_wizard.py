from pokemon.utils.enhanced_evmenu import EnhancedEvMenu as EvMenu
from evennia import create_object, search_object
from typeclasses.rooms import Room
from typeclasses.exits import Exit

#
# ─── NODE FUNCTIONS ─────────────────────────────────────────────────────────────
#
def node_start(caller, raw_input=None):
    """Entry point: initialize session data and ask for room name."""
    # store our collected data in the session
    caller.ndb.rw_data = {}
    text = (
        "Welcome to the Room Wizard!\n"
        "First: what will the |wname|n of the room be?"
    )
    # go to node_name next; capture any input with _default
    return text, [{"key": "_default", "goto": "node_name"}]

def node_name(caller, raw_input):
    """Collect room name and ask for description."""
    if not raw_input:
        return (
            "Please give me a name (or type |wquit|n to exit):",
            [{"key": "_default", "goto": "node_name"}],
        )
    caller.ndb.rw_data['name'] = raw_input
    text = "Great.  Now enter the |wdescription|n of the room:"
    return text, [{"key": "_default", "goto": "node_desc"}]

def node_desc(caller, raw_input):
    """Collect description and ask if it's a Pokémon Center."""
    if not raw_input:
        return "I need a description.  (or |wquit|n)", {"goto": "node_desc"}
    caller.ndb.rw_data['desc'] = raw_input
    text = "Is this a |wPokémon Center|n? (yes/no)"
    opts = [
        {"key": "yes", "goto": "node_center_yes"},
        {"key": "no", "goto": "node_center_no"},
    ]
    return text, opts

def node_center_yes(caller, raw_input=None):
    caller.ndb.rw_data['is_center'] = True
    return "Is this an |wItem Shop|n? (yes/no)", [
        {"key": "yes", "goto": "node_shop_yes"},
        {"key": "no", "goto": "node_shop_no"},
    ]

def node_center_no(caller, raw_input=None):
    caller.ndb.rw_data['is_center'] = False
    return "Is this an |wItem Shop|n? (yes/no)", [
        {"key": "yes", "goto": "node_shop_yes"},
        {"key": "no", "goto": "node_shop_no"},
    ]

def node_shop_yes(caller, raw_input=None):
    caller.ndb.rw_data['is_shop'] = True
    return "Allow |wPokémon hunting|n? (yes/no)", [
        {"key": "yes", "goto": "node_hunt_yes"},
        {"key": "no", "goto": "node_hunt_no"},
    ]

def node_shop_no(caller, raw_input=None):
    caller.ndb.rw_data['is_shop'] = False
    return "Allow |wPokémon hunting|n? (yes/no)", [
        {"key": "yes", "goto": "node_hunt_yes"},
        {"key": "no", "goto": "node_hunt_no"},
    ]

def node_hunt_yes(caller, raw_input=None):
    caller.ndb.rw_data['has_hunting'] = True
    text = (
        "Enter the encounter table as `name:rate, name:rate`.\n"
        "Example: |wRattata:60, Pidgey:40|n"
    )
    return text, [{"key": "_default", "goto": "node_hunt_table"}]

def node_hunt_no(caller, raw_input=None):
    caller.ndb.rw_data['has_hunting'] = False
    # skip straight to summary
    return node_summary(caller)

def node_hunt_table(caller, raw_input):
    data = caller.ndb.rw_data
    table = {}
    for entry in raw_input.split(","):
        try:
            mon, rate = entry.split(":")
            table[mon.strip()] = int(rate.strip())
        except ValueError:
            return (
                "Invalid format.  Use `name:rate, name:rate`.",
                {"goto": "node_hunt_table"}
            )
    data['hunt_table'] = table
    return node_summary(caller)

def node_summary(caller, raw_input=None):
    """Show summary and ask final confirm."""
    data = caller.ndb.rw_data
    text = (
        "|gRoom Creation Summary|n\n"
        f"Name:        {data['name']}\n"
        f"Description: {data['desc']}\n"
        f"Center:      {'Yes' if data.get('is_center') else 'No'}\n"
        f"Shop:        {'Yes' if data.get('is_shop') else 'No'}\n"
        f"Hunting:     {'Yes' if data.get('has_hunting') else 'No'}\n"
    )
    if data.get('has_hunting'):
        for mon, rate in data['hunt_table'].items():
            text += f"  - {mon}: {rate}%\n"
    text += "\nType |wcreate|n to finish or |wquit|n to abort."
    opts = [
        {"key": "create", "goto": "node_create"},
        {"key": "quit", "goto": "node_quit"},
    ]
    return text, opts

def node_create(caller, raw_input=None):
    """Actually create the room and exit."""
    data = caller.ndb.rw_data
    room = create_object(Room, key=data['name'])
    room.db.desc                = data['desc']
    room.db.is_pokemon_center   = data.get('is_center', False)
    room.db.is_item_shop        = data.get('is_shop', False)
    room.db.has_pokemon_hunting = data.get('has_hunting', False)
    room.db.hunt_table          = data.get('hunt_table', {})
    caller.msg(f"|gRoom '{room.key}' created successfully! (ID: {room.id})|n")
    caller.ndb.rw_room = room
    del caller.ndb.rw_data
    return (
        "Would you like to add exits to this room? (yes/no)",
        [
            {"key": "yes", "goto": "node_exit_dir"},
            {"key": "no", "goto": "node_tp_prompt"},
        ],
    )

def node_exit_dir(caller, raw_input=None):
    """Prompt for exit direction and destination."""
    room = caller.ndb.rw_room
    if not raw_input:
        text = (
            "Enter exit as <direction>=<room_id> or 'list rooms'.\n"
            "Type 'done' when finished."
        )
        return text, [{"key": "_default", "goto": "node_exit_dir"}]
    cmd = raw_input.strip()
    if cmd.lower().startswith("list"):
        lines = [f"{r.id} - {r.key}" for r in Room.objects.all()]
        caller.msg("\n".join(lines))
        return "Enter exit as <dir>=<id> or 'done':", {"goto": "node_exit_dir"}
    if cmd.lower() == "done":
        return node_tp_prompt(caller)
    if "=" not in cmd:
        caller.msg("Usage: <direction>=<room_id> or 'done'.")
        return "", {"goto": "node_exit_dir"}
    direction, rid = [s.strip() for s in cmd.split("=", 1)]
    try:
        dest = Room.objects.get(id=int(rid))
    except (ValueError, Room.DoesNotExist):
        caller.msg("Invalid room id.")
        return "", {"goto": "node_exit_dir"}
    create_object(Exit, key=direction, location=room, destination=dest)
    caller.msg(f"Created exit '{direction}' to {dest.key}.")
    return "Add another exit or 'done' when finished:", {"goto": "node_exit_dir"}

def node_tp_prompt(caller, raw_input=None):
    """Ask if caller wants to teleport into the room."""
    return (
        "Teleport to the new room now? (yes/no)",
        [
            {"key": "yes", "goto": "node_tp_yes"},
            {"key": "no", "goto": "node_quit"},
        ],
    )

def node_tp_yes(caller, raw_input=None):
    room = caller.ndb.rw_room
    if room:
        caller.move_to(room, quiet=True)
        caller.msg(f"You are now in {room.key}.")
    return node_quit(caller)

def node_quit(caller, raw_input=None):
    """Clean exit node (EvMenu tears itself down)."""
    if hasattr(caller.ndb, "rw_room"):
        del caller.ndb.rw_room
    if hasattr(caller.ndb, "rw_data"):
        del caller.ndb.rw_data
    return "Exiting Room Wizard.  Thanks!", None
