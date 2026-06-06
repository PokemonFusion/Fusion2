"""Commands for viewing trainer XP."""

from evennia import Command

from pokemon.models.stats import (
    get_trainer_xp,
    next_trainer_level_xp,
    trainer_level_for_xp,
)


def format_trainer_xp_status(character) -> str:
    """Return a compact trainer XP summary for ``character``."""

    txp = get_trainer_xp(character)
    level = trainer_level_for_xp(txp)
    lines = [
        f"|wTrainer Level|n: {level}",
        f"|wTXP|n: {txp:,}",
    ]
    if level < 100:
        next_req = next_trainer_level_xp(txp)
        remaining = max(0, next_req - txp)
        lines.append(f"|wNext Level|n: {next_req:,} TXP ({remaining:,} to go)")
    return "\n".join(lines)


class CmdTrainerXP(Command):
    """Show your trainer XP and trainer level.

    Usage:
      +txp

    Aliases:
      +trainerxp
      +trainerlevel
    """

    key = "+txp"
    aliases = ["+trainerxp", "+trainerlevel"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        self.caller.msg(format_trainer_xp_status(self.caller))
