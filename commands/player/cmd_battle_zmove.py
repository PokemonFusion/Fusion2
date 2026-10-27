"""Ordinary bounded Z-Move input, with fresh source-slot and target validation."""

from evennia import Command
from world.system_init import get_system
from .cmd_battle_utils import NOT_IN_BATTLE_MSG


class CmdBattleZMove(Command):
    """Use an accepted active move and reusable held crystal for one Z action.

    Usage:
      +zmove [acting slot]
      +zmove [acting slot] <active move slot or full name>=<target slot>

    With no move, show current choices without queueing anything. Doubles
    require your A1/A2 or B1/B2 actor. Only explicitly listed sources work;
    Normalium Z with Tackle becomes 100-power Physical Normal Breakneck Blitz.
    This queues one MOVE;
    no second +attack is needed. One Z use per side per battle, independent
    of Mega/Tera on a different ally. Prevention spends no PP/use; a started
    Z-Move spends one source PP and retains the crystal. No plot unlock.
    """

    key = "+zmove"
    aliases = ["+battle/zmove"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        """Resolve only current ordinary control, preserving all no-overwrite rules."""
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.z_moves import ZMoves

        if not getattr(self.caller.db, "battle_control", False):
            self.caller.msg("We aren't waiting for you to command right now.")
            return
        manager = getattr(get_system(), "battle_manager", None)
        session = manager.for_player(self.caller) if manager else None
        session = session or BattleSession.ensure_for_player(self.caller)
        if session is None or session.battle is None:
            self.caller.msg(NOT_IN_BATTLE_MSG)
            return
        source, separator, target = (self.args or "").partition("=")
        parts = source.strip().split(maxsplit=1)
        actor = None
        if parts and parts[0].upper() in {"A1", "A2", "B1", "B2"}:
            actor = parts[0].upper()
            source = parts[1].strip() if len(parts) > 1 else ""
        else:
            source = source.strip()
        try:
            choices = session.choices_for(self.caller)
            if not source and not separator:
                self.caller.msg(ZMoves.discover(choices, actor=actor))
            elif not source:
                raise ValueError("Choose an actual active move slot or full name.")
            else:
                choices.zmove(source, target.strip() if separator else None, actor=actor)
        except ValueError as error:
            self.caller.msg(str(error))
