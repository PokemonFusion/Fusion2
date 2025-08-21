"""Command to attempt fleeing from battle."""

from __future__ import annotations

from evennia import Command

from .cmd_battle_utils import NOT_IN_BATTLE_MSG, _get_participant

try:  # pragma: no cover - battle engine may not be available in tests
    from pokemon.battle import Action, ActionType
    if Action is None or ActionType is None:  # type: ignore[truthy-bool]
        raise ImportError
except Exception:  # pragma: no cover - fallback if engine isn't loaded
    from pokemon.battle.engine import Action, ActionType


class CmdBattleFlee(Command):
    """Attempt to flee from battle.

    Usage:
      +battle/flee
    """

    key = "+battle/flee"
    aliases = ["+flee", "+Flee", "+battleflee"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        if not getattr(self.caller.db, "battle_control", False):
            self.caller.msg("|rWe aren't waiting for you to command right now.")
            return
        try:  # pragma: no cover - battle session may be absent in tests
            from pokemon.battle.battleinstance import BattleSession
        except Exception:  # pragma: no cover
            class BattleSession:  # type: ignore[override]
                @staticmethod
                def ensure_for_player(caller):
                    return getattr(caller.ndb, "battle_instance", None)

        inst = BattleSession.ensure_for_player(self.caller)
        if not inst or not inst.battle:
            self.caller.msg(NOT_IN_BATTLE_MSG)
            return
        participant = _get_participant(inst, self.caller)
        action = Action(participant, ActionType.RUN, priority=9)
        participant.pending_action = action
        self.caller.msg("You attempt to flee!")
        if hasattr(inst, "queue_run"):
            try:
                inst.queue_run(caller=self.caller)
            except Exception:
                pass
        elif hasattr(inst, "maybe_run_turn"):
            try:
                inst.maybe_run_turn()
            except Exception:
                pass

