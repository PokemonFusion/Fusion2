from evennia.commands.default.account import CmdIC as DefaultCmdIC, CmdOOC as DefaultCmdOOC
from evennia import Command

class CmdGOIC(DefaultCmdIC):
    """Go in-character."""
    key = "goic"
    aliases = ["puppet"]

class CmdGOOOC(DefaultCmdOOC):
    """Go out-of-character."""
    key = "goooc"
    aliases = ["unpuppet"]

class CmdOOC(Command):
    """Speak or pose out-of-character in bright green."""
    key = "ooc"
    locks = "cmd:all()"
    arg_regex = None

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

