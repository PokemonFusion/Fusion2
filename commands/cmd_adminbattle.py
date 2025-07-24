from __future__ import annotations

from evennia import Command, search_object

from pokemon.battle.battleinstance import BattleSession

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
            inst = getattr(target.ndb, "battle_instance", None)
            if not inst:
                self.caller.msg("They are not currently in battle.")
                return
        bid = inst.battle_id
        inst.end()
        self.caller.msg(f"Battle #{bid} aborted.")


class CmdRestoreBattle(Command):
    """Restore a saved battle in the current room for debugging.

    Usage:
      +restorebattle <battle_id>
    """

    key = "+restorebattle"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +restorebattle <battle_id>")
            return

        arg = self.args.strip()
        if not arg.isdigit():
            self.caller.msg("Battle ID must be numeric.")
            return

        battle_id = int(arg)
        inst = BattleSession.restore(self.caller.location, battle_id)
        if not inst:
            self.caller.msg(f"Could not restore battle {battle_id}.")
        else:
            self.caller.msg(f"Restored battle {battle_id}.")
