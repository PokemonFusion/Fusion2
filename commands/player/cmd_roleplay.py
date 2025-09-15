from evennia import Command
from evennia.commands.default.account import CmdIC as DefaultCmdIC
from evennia.commands.default.account import CmdOOC as DefaultCmdOOC
from evennia.utils import logger


class CmdGOIC(DefaultCmdIC):
    """Go in-character.

    Usage:
      goic
      goic <character or number>
    """

    key = "goic"
    aliases = ["puppet"]
    help_category = "General"

    def parse(self):
        """Handle character numbers before executing the command."""

        super().parse()
        self._character_from_index = None
        self._index_error = None

        if not self.args:
            return

        stripped = self.args.strip()
        if not stripped.isdigit():
            return

        index = int(stripped)
        account = getattr(self, "account", None)
        character_list = []

        if account:
            stored = list(getattr(account.ndb, "character_selection_order", []) or [])
            if stored:
                character_list = [char for char in stored if char]
            else:
                playable = account.characters or []
                character_list = [char for char in playable if char]

        if not character_list:
            self._index_error = "You don't have a character with that number."
            return

        if index <= 0 or index > len(character_list):
            self._index_error = "That character number is not available."
            return

        self._character_from_index = character_list[index - 1]
        self.args = self._character_from_index.key

    def func(self):
        """Puppet a character by name or selection number."""

        if self._index_error:
            self.msg(self._index_error)
            return

        if self._character_from_index:
            account = self.account
            session = self.session
            new_character = self._character_from_index

            try:
                account.puppet_object(session, new_character)
                account.db._last_puppet = new_character
                logger.log_sec(
                    f"Puppet Success: (Caller: {account}, Target: {new_character}, IP:"
                    f" {self.session.address})."
                )
            except RuntimeError as exc:
                self.msg(f"|rYou cannot become |C{new_character.name}|n: {exc}")
                logger.log_sec(
                    f"Puppet Failed: %s (Caller: {account}, Target: {new_character}, IP:"
                    f" {self.session.address})."
                )
            return

        super().func()


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
                f'|w<OOC>|n |G{caller.name} says, "{speech}"|n',
                from_obj=caller,
            )
