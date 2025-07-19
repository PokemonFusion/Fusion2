from evennia import Command, search_object

class CmdWatch(Command):
    """Watch another trainer's ongoing battle.

    Usage:
      +watch <player>
    """

    key = "+watch"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +watch <player>")
            return
        targets = search_object(self.args.strip())
        if not targets:
            self.caller.msg("No such character.")
            return
        target = targets[0]
        inst = getattr(target.ndb, "battle_instance", None)
        if not inst:
            self.caller.msg("They are not currently in a battle.")
            return
        inst.add_observer(self.caller)

class CmdUnwatch(Command):
    """Stop watching the current battle.

    Usage:
      +unwatch
    """

    key = "+unwatch"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        inst = getattr(self.caller.ndb, "battle_instance", None)
        if not inst or self.caller not in inst.observers:
            self.caller.msg("You are not watching any battle.")
            return
        inst.remove_observer(self.caller)
        self.caller.msg("You stop watching the battle.")


