"""Challenge an explicitly enabled static trainer in the caller's room."""

from commands.admin.cmd_npcbattle import Command
from pokemon.battle.compat import log_warn
from pokemon.services.trainer_challenges import TrainerChallenge, retry_trainer_challenge_cleanup
from pokemon.services.trainer_encounters import TrainerEncounterError


class CmdChallenge(Command):
    """Challenge a placed trainer.

    Usage:
      +challenge <NPC name>
      +challenge/retry

    The NPC's configured single or double format is honored. Doubles requires
    two conscious party members. The NPC must be
    accepting challenges, rested, and free of another battle.
    """

    key = "+challenge"
    aliases = ["+challenge/retry"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        """Resolve only room contents and launch through the challenge policy."""
        if getattr(self, "cmdstring", "").lower() == "+challenge/retry":
            try:
                cleaned = retry_trainer_challenge_cleanup(self.caller)
            except Exception:
                log_warn("Placed trainer startup cleanup retry failed", exc_info=True)
                self.caller.msg("Challenge cleanup is still unavailable. Try +challenge/retry again shortly.")
                return
            self.caller.msg(
                "Failed challenge startup cleaned up. You can challenge that trainer again."
                if cleaned else "There is no failed challenge startup waiting for cleanup."
            )
            return
        name = (self.args or "").strip()
        if not name:
            self.caller.msg("Usage: +challenge <NPC name>")
            return
        if self.caller.location is None:
            self.caller.msg("You must be in a room to challenge a trainer.")
            return
        npc = self.caller.search(name, candidates=self.caller.location.contents)
        if npc is None:
            return
        try:
            session, encounter = TrainerChallenge(self.caller, npc).start()
        except TrainerEncounterError as err:
            self.caller.msg(str(err))
            return
        except Exception:
            log_warn("Placed trainer challenge startup failed", exc_info=True)
            self.caller.msg(
                "The trainer challenge could not start. Ask staff to check the battle service before retrying."
            )
            return
        self.caller.msg(f"Started trainer challenge #{session.battle_id} against {encounter.display_name}.")
