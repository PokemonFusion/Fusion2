# coding: utf-8
"""Room creation wizard command."""

from evennia import Command, create_object
from typeclasses.rooms import Room


class CmdRoomWizard(Command):
    """Interactive wizard for creating rooms."""

    key = "@roomwizard"
    locks = "cmd:perm(Builders)"
    help_category = "Building"

    def show_summary(self, caller, data):
        """Display a summary of collected room data."""
        msg = "|gRoom Creation Summary|n\n"
        msg += f"Name: {data.get('name', '???')}\n"
        msg += f"Description: {data.get('desc', '???')}\n"
        msg += f"Is Pokémon Center: {'Yes' if data.get('is_center') else 'No'}\n"
        msg += f"Is Item Shop: {'Yes' if data.get('is_shop') else 'No'}\n"
        msg += f"Hunting Enabled: {'Yes' if data.get('has_hunting') else 'No'}\n"
        if data.get('has_hunting'):
            table = data.get('hunt_table', {})
            msg += "Hunt Table:\n"
            for mon, rate in table.items():
                msg += f"  - {mon}: {rate}%\n"
        msg += "\nType |wcreate|n to finalize room creation or |wcancel|n to abort."
        caller.msg(msg)

    def func(self):
        caller = self.caller
        state = caller.ndb.rw_state
        data = caller.ndb.rw_data or {}

        if not state:
            caller.ndb.rw_state = 'name'
            caller.ndb.rw_data = {}
            caller.msg('|gRoom Wizard:|n What will the name of the room be?')
            return

        text = self.args.strip()

        if state == 'name':
            if not text:
                caller.msg("Please enter a room name.")
                return
            data['name'] = text
            caller.ndb.rw_state = 'desc'
            caller.ndb.rw_data = data
            caller.msg('|gRoom Wizard:|n What is the description of the room?')

        elif state == 'desc':
            if not text:
                caller.msg("Please enter a description.")
                return
            data['desc'] = text
            caller.ndb.rw_state = 'is_center'
            caller.ndb.rw_data = data
            caller.msg('|gRoom Wizard:|n Is this a Pokémon Center? (yes/no)')

        elif state == 'is_center':
            data['is_center'] = text.lower() == 'yes'
            caller.ndb.rw_state = 'is_shop'
            caller.ndb.rw_data = data
            caller.msg('|gRoom Wizard:|n Is this an Item Shop? (yes/no)')

        elif state == 'is_shop':
            data['is_shop'] = text.lower() == 'yes'
            caller.ndb.rw_state = 'has_hunting'
            caller.ndb.rw_data = data
            caller.msg('|gRoom Wizard:|n Allow Pokémon hunting in this room? (yes/no)')

        elif state == 'has_hunting':
            data['has_hunting'] = text.lower() == 'yes'
            if data['has_hunting']:
                caller.ndb.rw_state = 'hunt_table'
                caller.ndb.rw_data = data
                caller.msg('|gRoom Wizard:|n Enter Pokémon encounter table as: name:rate, name:rate (e.g. Rattata:60, Pidgey:40)')
            else:
                caller.ndb.rw_state = 'summary'
                caller.ndb.rw_data = data
                self.show_summary(caller, data)

        elif state == 'hunt_table':
            entries = text.split(',')
            table = {}
            for entry in entries:
                if not entry.strip():
                    continue
                try:
                    mon, rate = entry.strip().split(':')
                    table[mon.strip()] = int(rate.strip())
                except ValueError:
                    caller.msg('|rInvalid format.|n Use name:rate, e.g. Pidgey:50, Rattata:50')
                    return
            data['hunt_table'] = table
            caller.ndb.rw_state = 'summary'
            caller.ndb.rw_data = data
            self.show_summary(caller, data)

        elif state == 'summary':
            caller.msg("Type |wcreate|n to finalize or |wcancel|n to abort.")
            caller.ndb.rw_state = 'confirm'
            caller.ndb.rw_data = data

        elif state == 'confirm':
            choice = text.lower()
            if choice == 'cancel':
                caller.msg('|rRoom creation canceled.|n')
                caller.ndb.rw_state = None
                caller.ndb.rw_data = None
                return
            if choice != 'create':
                caller.msg("Type |wcreate|n to confirm or |wcancel|n to abort.")
                return

            room = create_object(Room, key=data['name'])
            room.db.desc = data['desc']
            room.db.is_pokemon_center = data.get('is_center', False)
            room.db.is_item_shop = data.get('is_shop', False)
            room.db.has_pokemon_hunting = data.get('has_hunting', False)
            room.db.hunt_table = data.get('hunt_table', {})

            caller.msg(f"|gRoom '{room.key}' created successfully!|n")
            caller.ndb.rw_state = None
            caller.ndb.rw_data = None

