from evennia import Command
from evennia.utils.utils import inherits_from

from pokemon.battle.pvp import (
    create_request,
    remove_request,
    find_request,
    get_requests,
    start_pvp_battle,
)


class CmdPvpHelp(Command):
    """Show available PVP commands.

    Usage:
      +pvp
    """

    key = "+pvp"
    locks = "cmd:all()"
    help_category = "Pokemon/PvP"

    def func(self):
        lines = ["|wPlayer vs Player commands|n"]
        lines.append("  +pvp/list - list open PVP requests")
        lines.append("  +pvp/create [password] - create a PVP request")
        lines.append("  +pvp/join <player> [password] - join a request")
        lines.append("  +pvp/abort - abort your request")
        lines.append("  +pvp/start - start the battle when ready")
        self.caller.msg("\n".join(lines))


class CmdPvpList(Command):
    """List all open PVP requests in the room.

    Usage:
      +pvp/list
    """

    key = "+pvp/list"
    locks = "cmd:all()"
    help_category = "Pokemon/PvP"

    def func(self):
        reqs = get_requests(self.caller.location)
        if not reqs:
            self.caller.msg("No active PVP requests here.")
            return
        lines = ["|wActive PVP requests|n"]
        for req in reqs.values():
            status = "(joined)" if req.opponent_id is not None else ""
            lines.append(f"  {req.host_key} {status}")
        self.caller.msg("\n".join(lines))


class CmdPvpCreate(Command):
    """Create a new PVP request.

    Usage:
      +pvp/create [password]
    """

    key = "+pvp/create"
    locks = "cmd:all()"
    help_category = "Pokemon/PvP"

    def func(self):
        password = self.args.strip() or None
        try:
            create_request(self.caller, password=password)
        except ValueError as err:
            self.caller.msg(str(err))
            return
        self.caller.msg("PVP request created.")


class CmdPvpJoin(Command):
    """Join an existing PVP request.

    Usage:
      +pvp/join <player> [password]
    """

    key = "+pvp/join"
    locks = "cmd:all()"
    help_category = "Pokemon/PvP"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +pvp/join <player> [password]")
            return
        parts = self.args.split()
        host_name = parts[0]
        password = parts[1] if len(parts) > 1 else None
        req = find_request(self.caller.location, host_name)
        if not req:
            self.caller.msg("No joinable request found.")
            return
        if getattr(req, "host_id", None) == self.caller.id:
            self.caller.msg("You cannot join your own PVP request.")
            return

        def _finish_join(passwd: str) -> None:
            if req.password and req.password != passwd:
                self.caller.msg("Incorrect password.")
                return
            if not req.is_joinable():
                self.caller.msg("No joinable request found.")
                return
            req.opponent_id = self.caller.id
            self.caller.msg(f"You join {req.host_key}'s PVP request.")
            host = req.get_host()
            if host:
                host.msg(f"{self.caller.key} has joined your PVP request.")

        if req.password and password is None:
            from evennia.utils.evmenu import get_input

            def _callback(caller, prompt, result):
                _finish_join(result.strip())
                return False

            get_input(self.caller, "Password:", _callback)
            return

        _finish_join(password)


class CmdPvpAbort(Command):
    """Abort your active PVP request.

    Usage:
      +pvp/abort
    """

    key = "+pvp/abort"
    locks = "cmd:all()"
    help_category = "Pokemon/PvP"

    def func(self):
        remove_request(self.caller)
        self.caller.msg("PVP request aborted.")


class CmdPvpStart(Command):
    """Start a PVP battle.

    Usage:
      +pvp/start
    """

    key = "+pvp/start"
    locks = "cmd:all()"
    help_category = "Pokemon/PvP"

    def func(self):
        reqs = get_requests(self.caller.location)
        req = reqs.get(self.caller.id)
        if not req:
            self.caller.msg("You are not hosting a PVP request.")
            return
        if req.opponent_id is None:
            self.caller.msg("No opponent has joined yet.")
            return
        if getattr(self.caller.ndb, "battle_instance", None):
            self.caller.msg("You are already engaged in a battle.")
            return

        opponent = req.get_opponent()
        if opponent and getattr(opponent.ndb, "battle_instance", None):
            self.caller.msg("Your opponent is already engaged in a battle.")
            return

        remove_request(self.caller)
        start_pvp_battle(self.caller, opponent)

