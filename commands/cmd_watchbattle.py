"""Commands to watch or unwatch ongoing battles."""

from __future__ import annotations

from evennia import Command
from evennia import search_object

from pokemon.battle.interface import add_watcher, remove_watcher


class CmdWatchBattle(Command):
    """Watch another character's ongoing battle.

    Usage:
      +watchbattle <character or battle id>
    """

    key = "+watchbattle"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +watchbattle <character or battle id>")
            return
        arg = self.args.strip()
        inst = None
        target = None
        if arg.isdigit():
            from pokemon.battle.handler import battle_handler

            bid = int(arg)
            inst = battle_handler.instances.get(bid)
            if not inst:
                self.caller.msg("No battle with that ID found.")
                return
        else:
            target_list = search_object(arg)
            if not target_list:
                self.caller.msg("No such character.")
                return
            target = target_list[0]
            inst = getattr(target.ndb, "battle_instance", None)
            if not inst:
                self.caller.msg("They are not currently in battle.")
                return
        inst.add_watcher(self.caller)
        self.caller.move_to(inst.room, quiet=True)
        if target:
            self.caller.msg(
                f"You begin watching {target.key}'s battle (#{inst.room.id})."
            )
        else:
            self.caller.msg(f"You begin watching battle #{inst.room.id}.")


class CmdUnwatchBattle(Command):
    """Stop watching the current battle.

    Usage:
      +unwatchbattle
    """

    key = "+unwatchbattle"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        inst = (
            self.caller.location.ndb.instance if self.caller.location else None
        )
        if not inst or not hasattr(inst, "remove_watcher"):
            self.caller.msg("You are not watching a battle.")
            return
        inst.remove_watcher(self.caller)
        self.caller.msg("You stop watching the battle.")
        self.caller.move_to(inst.room.home or self.caller.home, quiet=True)
