"""Explicit reviewed native Ultra Burst terms before an ordinary battle attack."""

from evennia import Command

from world.system_init import get_system
from .cmd_battle_utils import NOT_IN_BATTLE_MSG


class CmdBattleUltra(Command):
    """Review and reserve a native Ultra Burst without spending an extra action.

    Usage:
      +ultra [acting slot]
      +ultra [acting slot] cancel

    Review the yes/no preview, then use +attack. Requires your genuine paired
    Dusk Mane/Dawn Wings, native active Prism Armor, physical Ultranecrozium Z
    and separately active legitimate Photon Geyser. Doubles require an actor.
    Photon may be at0 PP for activation; a later signature needs current PP.
    One Ultra use per side, separate from Z. The crystal stays reusable.
    """

    key = "+ultra"
    aliases = ["+battle/ultra"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        """Revalidate the exact reviewed terms after the player's explicit yes."""
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.ultra_burst import UltraBurst

        cancel_requested = bool(
            (self.args or "").split() and (self.args or "").split()[-1].casefold() == "cancel"
        )
        if not cancel_requested and not getattr(self.caller.db, "battle_control", False):
            self.caller.msg("We aren't waiting for you to command right now.")
            return
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
            self.caller.msg("Usage: +ultra [acting slot] [cancel]")
            return
        actor = args[0] if args else None
        try:
            if cancel:
                UltraBurst.choose(session.choices_for(self.caller), actor=actor, cancel=True)
                return
            reviewed = UltraBurst.choose(session.choices_for(self.caller), actor=actor)
            prep = reviewed["preparation"]
            answer = yield (
                f"Ultra Burst: {prep['native']} becomes Necrozma-Ultra with Neuroforce. "
                f"Photon Geyser slot {prep['photon_slot']}: {prep['current_pp']}/{prep['capacity']} PP. "
                "Activation spends your side's Ultra use with your next ordinary attack; no PP or crystal debit. "
                "The signature needs a later completed turn, positive Photon PP and an unused Z budget. "
                "Confirm these current terms? [yes/no]"
            )
            if str(answer).strip().casefold() not in {"yes", "y"}:
                self.caller.msg("Ultra preview declined; no declaration was reserved.")
                return
            current = manager.for_player(self.caller) if manager else None
            current = current or BattleSession.ensure_for_player(self.caller)
            if current is None:
                raise ValueError("The battle changed. Reopen +ultra to review current terms.")
            UltraBurst.choose(current.choices_for(self.caller), actor=actor, reviewed=reviewed)
        except ValueError as error:
            self.caller.msg(str(error))
