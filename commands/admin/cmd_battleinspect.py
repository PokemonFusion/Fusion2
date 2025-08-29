"""Administrative command for dumping the state of an active battle."""
from __future__ import annotations

import json
from typing import Any

from evennia import Command
from evennia.utils.search import search_object

from world.system_init import get_system


class CmdBattleInspect(Command):
    """Dump raw state information about an active battle.

    Usage:
        +battleinspect <battle id or player>

    When given a numeric battle id, the command looks up the active battle
    managed by ``BattleManager`` and returns its internal state dictionary. If
    a non-numeric argument is supplied, the command attempts to resolve it to a
    player or character and inspects the battle they are currently involved
    in.  Output is formatted as JSON for readability.
    """

    key = "+battleinspect"
    aliases = ["battleinspect"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def _get_instance(self, arg: str) -> Any:
        """Return the battle instance referenced by ``arg`` if any."""

        system = get_system()
        manager = getattr(system, "battle_manager", None)
        if not manager:
            return None
        if arg.isdigit():
            return manager.get(int(arg))
        target = search_object(arg)
        if target:
            return manager.for_player(target[0])
        return None

    def func(self) -> None:  # type: ignore[override]
        """Execute the battle inspection."""

        if not self.args:
            self.caller.msg("Usage: +battleinspect <battle id or player>")
            return
        inst = self._get_instance(self.args.strip())
        if not inst:
            self.caller.msg("No active battle found for that target.")
            return
        state = getattr(getattr(inst, "db", None), "state", {})
        try:
            text = json.dumps(state, indent=2, sort_keys=True)
        except Exception:
            text = str(state)
        self.caller.msg(text)


__all__ = ["CmdBattleInspect"]

