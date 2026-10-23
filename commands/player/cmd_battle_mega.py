"""Ordinary native Mega reservation; no plot unlock or extra battle action."""

from evennia import Command

from world.system_init import get_system
from .cmd_battle_utils import NOT_IN_BATTLE_MSG


class CmdBattleMega(Command):
    """Reserve a reusable Mega Evolution for your active Pokemon's next move.

    Usage:
      +mega [acting slot]
      +mega [acting slot] cancel

    Choose Mega before +attack. Doubles require your A1/A2 or B1/B2 actor.
    Initially only native Venusaur holding Venusaurite is accepted. One use per
    side per battle, separate from Tera on a different ally. No ring, quest,
    activation fee or bag debit. Invalid input keeps your reservation; a legal
    switch, item or flee cancels it. The stone stays reusable after battle.
    """

    key = "+mega"
    aliases = ["+battle/mega"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        """Resolve current control and delegate validation/persistence to choices."""
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
        cancel = bool(args and args[-1].casefold() == "cancel")
        if cancel:
            args.pop()
        if len(args) > 1:
            self.caller.msg("Usage: +mega [acting slot] [cancel]")
            return
        try:
            session.choices_for(self.caller).mega(actor=args[0] if args else None, cancel=cancel)
        except ValueError as error:
            self.caller.msg(str(error))
