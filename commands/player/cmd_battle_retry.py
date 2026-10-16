"""Recover saved battle rewards without replaying attacks or item use."""

from evennia import Command

from pokemon.battle.battleinstance import BattleSession
from pokemon.battle.compat import log_warn
from pokemon.services.battle_rewards import PENDING_MESSAGE, BattleRewards


class CmdBattleRetry(Command):
    """Retry pending battle rewards and terminal cleanup.

    Usage:
      +battle/retry
    """

    key = "+battle/retry"
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self):
        """Recover only this character's receipts, preserving any active battle."""
        try:
            session = BattleSession.ensure_for_player(self.caller)
            if session is not None:
                session.retry_battle_rewards()
                if session.turn_state.get("error") or (
                    session.state is not None and session.state.declare and session.is_turn_ready()
                    and not session.state.ending and not getattr(session.battle, "battle_over", False)
                ):
                    session.run_turn()
                    if session.turn_state.get("error"):
                        self.caller.msg(PENDING_MESSAGE)
                    else:
                        self.caller.msg("The retained turn was recovered.")
                    return
                battle = session.battle
                if battle is None:
                    self.caller.msg("There is no active battle to recover.")
                    return
                battle.run_faint()
                winner = battle.check_win_conditions()
                if winner or battle.battle_over or getattr(session.state, "ending", False):
                    session._handle_battle_result(winner)
                    session.end()
                    self.caller.msg("Battle rewards and cleanup recovered.")
                else:
                    session._sync_active_battle_state()
                    session._persist_turn_state()
                    session.prompt_next_turn()
                    self.caller.msg("Pending rewards recovered. Your battle can continue.")
                return
            count = 0
            for key in BattleRewards.pending(self.caller):
                rewards = BattleRewards(key.split(":", 1)[0])
                count += bool(rewards.claim(self.caller, key))
            self.caller.msg("Pending battle rewards recovered." if count else "There are no pending battle rewards.")
        except Exception:
            log_warn("Battle reward recovery failed", exc_info=True)
            self.caller.msg(PENDING_MESSAGE)
