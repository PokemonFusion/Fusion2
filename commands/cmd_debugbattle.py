"""Command to toggle battle debug output."""

from __future__ import annotations

from evennia import Command, search_object


class CmdDebugBattle(Command):
    """Toggle debug output for an active battle.

    Usage:
      +debug/battle <character or battle id>
    """

    key = "+debug/battle"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):  # type: ignore[override]
        if not self.args:
            self.caller.msg("Usage: +debug/battle <character or battle id>")
            return
        arg = self.args.strip()
        inst = None
        if arg.isdigit():
            from pokemon.battle.handler import battle_handler

            inst = battle_handler.instances.get(int(arg))
        else:
            targets = search_object(arg)
            if targets:
                target = targets[0]
                inst = getattr(target.ndb, "battle_instance", None)
        if not inst or not getattr(inst, "state", None):
            self.caller.msg("No active battle found.")
            return
        state = inst.state
        state.debug = not getattr(state, "debug", False)
        if inst.battle:
            inst.battle.debug = state.debug
        try:
            inst.storage.set("state", state.to_dict())
        except Exception:
            pass
        status = "enabled" if state.debug else "disabled"
        inst.notify(f"[DEBUG] Battle debug {status} by {getattr(self.caller, 'key', self.caller)}.")
        self.caller.msg(f"Battle debug {status}.")
