from evennia.utils.evmenu import EvMenu
from evennia import create_object
from typeclasses.rooms import Room

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
    # go to node_name next
    return text, {"goto": "node_name"}

def node_name(caller, raw_input):
    """Collect room name and ask for description."""
    if not raw_input:
        return "Please give me a name (or type |wquit|n to exit):", {"goto": "node_name"}
    caller.ndb.rw_data['name'] = raw_input
    text = "Great.  Now enter the |wdescription|n of the room:"
    return text, {"goto": "node_desc"}

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
    return text, {"goto": "node_hunt_table"}

def node_hunt_no(caller, raw_input=None):
    caller.ndb.rw_data['has_hunting'] = False
    # skip straight to summary
    return None, {"goto": "node_summary"}

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
    return None, {"goto": "node_summary"}

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
    # clear out our session data
    del caller.ndb.rw_data
    return None, {"goto": "node_quit"}

def node_quit(caller, raw_input=None):
    """Clean exit node (EvMenu tears itself down)."""
    return "Exiting Room Wizard.  Thanks!", None
