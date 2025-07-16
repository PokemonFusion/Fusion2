from evennia.commands.default.account import CmdIC as DefaultCmdIC, CmdOOC as DefaultCmdOOC
from evennia import Command

class CmdGOIC(DefaultCmdIC):
    """Go in-character.

    Usage:
      goic
    """

    key = "goic"
    aliases = ["puppet"]
    help_category = "General"

class CmdGOOOC(DefaultCmdOOC):
    """Go out-of-character.

    Usage:
      goooc
    """

    key = "goooc"
    aliases = ["unpuppet"]
    help_category = "General"

class CmdOOC(Command):
    """Speak or pose out-of-character in bright green.

    Usage:
      ooc <message>
      ooc :<pose>
    """

    key = "ooc"
    locks = "cmd:all()"
    arg_regex = None
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Usage: ooc <message> | ooc :<pose>")
            return
        if self.args.startswith(":"):
            pose = self.args[1:].lstrip()
            msg = f"|w<OOC>|n |G{caller.name} {pose}|n"
            if caller.location:
                caller.location.msg_contents(msg, from_obj=caller)
            else:
                caller.msg(msg)
        else:
            speech = caller.at_pre_say(self.args)
            if not speech:
                return
            caller.location.msg_contents(
                f"|w<OOC>|n |G{caller.name} says, \"{speech}\"|n",
                from_obj=caller,
            )

