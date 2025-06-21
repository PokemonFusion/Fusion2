from __future__ import annotations

from evennia import Command, search_object

from pokemon.battle.pvp import PvpRequest, start_pvp_battle
from pokemon.battle.battleinstance import BattleInstance


class CmdPVPHelp(Command):
    """Show help for PVP commands."""

    key = "+pvp"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        self.caller.msg("PVP commands:")
        self.caller.msg("  +pvp/list - show active requests")
        self.caller.msg("  +pvp/create - create a request")
        self.caller.msg("  +pvp/join <player> - join a request")
        self.caller.msg("  +pvp/abort - abort your request")
        self.caller.msg("  +pvp/start - start once both players joined")


class CmdPVPList(Command):
    """List active PVP requests in the room."""

    key = "+pvp/list"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        requests = []
        for obj in self.caller.location.contents:
            req = getattr(obj.ndb, "pvp_request", None)
            if req:
                requests.append(f"{obj.key} (team size {req.team_size})")
        if not requests:
            self.caller.msg("No active requests here.")
            return
        self.caller.msg("Active PVP requests:")
        for line in requests:
            self.caller.msg(f"  {line}")


class CmdPVPCreate(Command):
    """Create a new PVP request."""

    key = "+pvp/create"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        self.args = self.args.strip()
        self.password = None
        self.team_size = 6
        self.how_many = 1
        for part in self.args.split():
            if part.startswith("password="):
                self.password = part.split("=", 1)[1]
            elif part.startswith("teamsize="):
                try:
                    self.team_size = int(part.split("=", 1)[1])
                except ValueError:
                    pass
            elif part.startswith("howmany="):
                try:
                    self.how_many = int(part.split("=", 1)[1])
                except ValueError:
                    pass

    def func(self):
        if getattr(self.caller.ndb, "pvp_request", None):
            self.caller.msg("You already have an active request.")
            return
        req = PvpRequest(host=self.caller, password=self.password, how_many=self.how_many, team_size=self.team_size)
        self.caller.ndb.pvp_request = req
        self.caller.location.msg_contents(f"{self.caller.key} is looking to battle! Use +pvp/join {self.caller.key} to accept.")


class CmdPVPJoin(Command):
    """Join another player's PVP request."""

    key = "+pvp/join"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +pvp/join <player>")
            return
        target = search_object(self.args.strip())
        if not target:
            self.caller.msg("No such player.")
            return
        target = target[0]
        req: PvpRequest = getattr(target.ndb, "pvp_request", None)
        if not req:
            self.caller.msg("That player is not offering a battle.")
            return
        if req.password:
            self.caller.msg("This battle is password protected.")
            return
        if req.opponent:
            self.caller.msg("Someone has already joined that battle.")
            return
        req.opponent = self.caller
        self.caller.ndb.pvp_request = req
        self.caller.location.msg_contents(f"{self.caller.key} joins {target.key}'s battle request.")


class CmdPVPAbort(Command):
    """Abort your active PVP request."""

    key = "+pvp/abort"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        req = getattr(self.caller.ndb, "pvp_request", None)
        if not req:
            self.caller.msg("You have no active request.")
            return
        self.caller.ndb.pvp_request = None
        if req.opponent and req.opponent.ndb.pvp_request:
            req.opponent.ndb.pvp_request = None
        self.caller.location.msg_contents(f"{self.caller.key} cancels the PVP request.")


class CmdPVPStart(Command):
    """Start a joined PVP battle."""

    key = "+pvp/start"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        req: PvpRequest = getattr(self.caller.ndb, "pvp_request", None)
        if not req:
            self.caller.msg("You have no active request.")
            return
        if req.host != self.caller:
            self.caller.msg("Only the host can start the battle.")
            return
        if not req.opponent:
            self.caller.msg("No one has joined your battle yet.")
            return
        inst = start_pvp_battle(req)
        if inst:
            self.caller.msg("Battle starting!")
            req.opponent.msg("Battle starting!")
        else:
            self.caller.msg("Could not start battle.")


