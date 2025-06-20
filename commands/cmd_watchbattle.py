"""Commands to watch or unwatch ongoing battles."""

from __future__ import annotations

from evennia import Command
from evennia import search_object

from pokemon.battle.interface import add_watcher, remove_watcher


class CmdWatchBattle(Command):
    """Watch another character's ongoing battle."""

    key = "+watchbattle"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +watchbattle <character>")
            return
        target = search_object(self.args.strip())
        if not target:
            self.caller.msg("No such character.")
            return
        target = target[0]
        inst = target.ndb.get("battle_instance")
        if not inst:
            self.caller.msg("They are not currently in battle.")
            return
        inst.add_watcher(self.caller)
        self.caller.move_to(inst.room, quiet=True)
        self.caller.msg(f"You begin watching {target.key}'s battle.")


class CmdUnwatchBattle(Command):
    """Stop watching the current battle."""

    key = "+unwatchbattle"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        inst = self.caller.location.db.instance if self.caller.location else None
        if not inst or not hasattr(inst, "remove_watcher"):
            self.caller.msg("You are not watching a battle.")
            return
        inst.remove_watcher(self.caller)
        self.caller.msg("You stop watching the battle.")
        self.caller.move_to(inst.room.home or self.caller.home, quiet=True)
