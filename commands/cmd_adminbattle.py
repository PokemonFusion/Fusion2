from __future__ import annotations

from evennia import Command, search_object

from pokemon.battle.handler import battle_handler


class CmdAbortBattle(Command):
    """Force end an ongoing battle.

    Usage:
      +abortbattle <character or battle id>
    """

    key = "+abortbattle"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +abortbattle <character or battle id>")
            return
        arg = self.args.strip()
        inst = None
        if arg.isdigit():
            inst = battle_handler.instances.get(int(arg))
            if not inst:
                self.caller.msg("No battle with that ID found.")
                return
        else:
            targets = search_object(arg)
            if not targets:
                self.caller.msg("No such character.")
                return
            target = targets[0]
            inst = target.ndb.get("battle_instance")
            if not inst:
                self.caller.msg("They are not currently in battle.")
                return
        bid = inst.room.id
        inst.end()
        self.caller.msg(f"Battle #{bid} aborted.")
