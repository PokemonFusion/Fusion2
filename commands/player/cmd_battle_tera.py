"""Ordinary player command for reserving Terastallization."""

from evennia import Command

from world.system_init import get_system

from .cmd_battle_utils import NOT_IN_BATTLE_MSG


class CmdBattleTera(Command):
    """Terastallize your active Pokemon with its next move.

    Usage:
      +tera [acting slot]
      +tera [acting slot] cancel

    Choose Tera before +attack. In doubles, specify A1/A2 (or B1/B2).
    Your side can Terastallize once per battle. Switching, items or fleeing
    cancel an unused reservation. No item or recharge is required.
    """

    key = "+tera"
    aliases = ["+battle/tera", "+terastallize"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        """Resolve the current session and use its authoritative choice boundary."""
        if not getattr(self.caller.db, "battle_control", False):
            self.caller.msg("We aren't waiting for you to command right now.")
            return
        from pokemon.battle.battleinstance import BattleSession

        manager = getattr(get_system(), "battle_manager", None)
        session = manager.for_player(self.caller) if manager else None
        session = session or BattleSession.ensure_for_player(self.caller)
        if session is None or session.battle is None:
            self.caller.msg(NOT_IN_BATTLE_MSG)
            return
        args = (self.args or "").split()
        cancel = bool(args and args[-1].lower() == "cancel")
        if cancel:
            args.pop()
        if len(args) > 1:
            self.caller.msg("Usage: +tera [acting slot] [cancel]")
            return
        try:
            session.choices_for(self.caller).tera(actor=args[0] if args else None, cancel=cancel)
        except ValueError as error:
            self.caller.msg(str(error))
