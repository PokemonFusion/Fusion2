"""Challenge an explicitly enabled static trainer in the caller's room."""

from commands.admin.cmd_npcbattle import Command
from pokemon.battle.compat import log_warn
from pokemon.services.trainer_challenges import TrainerChallenge
from pokemon.services.trainer_encounters import TrainerEncounterError


class CmdChallenge(Command):
    """Challenge a placed trainer.

    Usage:
      +challenge <NPC name>

    You need a conscious party (two Pokemon for doubles). The NPC must be
    accepting challenges, rested, and free of another battle.
    """

    key = "+challenge"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        """Resolve only room contents and launch through the challenge policy."""
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
