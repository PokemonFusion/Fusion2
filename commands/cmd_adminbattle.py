from __future__ import annotations

from evennia import Command, search_object
import pprint

from pokemon.battle.battleinstance import BattleSession
from pokemon.battle.storage import BattleDataWrapper

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


class CmdBattleInfo(Command):
    """Display stored battle data for debugging.

    Usage:
      +battleinfo <character or battle id>
    """

    key = "+battleinfo"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +battleinfo <character or battle id>")
            return

        arg = self.args.strip()
        inst = None
        room = None
        bid = None

        if arg.isdigit():
            bid = int(arg)
            inst = battle_handler.instances.get(bid)
            if inst:
                room = inst.room
        else:
            targets = search_object(arg)
            if not targets:
                self.caller.msg("No such character.")
                return
            target = targets[0]
            inst = getattr(target.ndb, "battle_instance", None)
            if inst:
                bid = inst.battle_id
                room = inst.room
            else:
                bid = getattr(target.db, "battle_id", None)
                room = target.location

        if bid is None or room is None:
            self.caller.msg("No battle data found.")
            return

        storage = BattleDataWrapper(room, bid)
        parts = {
            "data": storage.get("data"),
            "state": storage.get("state"),
            "trainers": storage.get("trainers"),
            "temp_pokemon_ids": storage.get("temp_pokemon_ids"),
        }

        lines = [f"Battle {bid} info:"]
        for key, value in parts.items():
            if value is not None:
                formatted = pprint.pformat(value, indent=2, width=78)
                lines.append(f"{key.capitalize()}:\n{formatted}")

        if len(lines) == 1:
            self.caller.msg("No stored data for that battle.")
        else:
            self.caller.msg("\n".join(lines))


class CmdRetryTurn(Command):
    """Retry the current turn of a battle."""

    key = "+retryturn"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +retryturn <character or battle id>")
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

        inst.run_turn()
        self.caller.msg(f"Turn retried for battle {inst.battle_id}.")
