"""Administrative trainer XP tools."""

from evennia import Command

from commands.player.cmd_trainer_xp import format_trainer_xp_status
from pokemon.models.stats import get_trainer_xp, set_trainer_xp, trainer_level_for_xp


def _parse_slash_switches(command) -> set[str]:
    """Extract slash switches for bare Command subclasses."""

    switches: list[str] = []
    for switch in getattr(command, "switches", []) or []:
        switches.extend(part for part in str(switch).lower().split("/") if part)

    cmdstring = str(getattr(command, "cmdstring", "") or "").lower()
    if "/" in cmdstring:
        _, switch_text = cmdstring.split("/", 1)
        switches.extend(part for part in switch_text.split("/") if part)

    raw_args = (command.args or "").strip()
    if raw_args.startswith("/") and len(raw_args) > 1:
        switch_text, _, raw_args = raw_args[1:].partition(" ")
        switches.extend(part for part in switch_text.lower().split("/") if part)
        command.args = raw_args.strip()

    return set(switches)


class CmdAdminTrainerXP(Command):
    """Inspect or adjust a character's trainer XP.

    Usage:
      @txp <character>
      @txp/add <character>=<amount>
      @txp/set <character>=<amount>

    Notes:
      /add accepts signed whole numbers and clamps the final TXP to zero.
      /set requires a non-negative whole number.
    """

    key = "@txp"
    aliases = ["@trainerxp"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def parse(self):
        switches = _parse_slash_switches(self)
        self.action = "show"
        if "set" in switches:
            self.action = "set"
        elif "add" in switches or "adjust" in switches:
            self.action = "add"

        args = (self.args or "").strip()
        self.target_expr = args
        self.amount_expr = ""
        if "=" in args:
            self.target_expr, self.amount_expr = [part.strip() for part in args.split("=", 1)]

    def _usage(self) -> str:
        return "Usage: @txp <character> OR @txp/add <character>=<amount> OR @txp/set <character>=<amount>"

    def func(self):
        if not self.target_expr:
            self.caller.msg(self._usage())
            return

        target = self.caller.search(self.target_expr, global_search=True)
        if not target:
            return
        is_typeclass = getattr(target, "is_typeclass", None)
        if callable(is_typeclass) and not target.is_typeclass("evennia.objects.objects.DefaultCharacter", exact=False):
            self.caller.msg("You can only manage TXP for characters.")
            return

        if self.action == "show":
            if self.amount_expr:
                self.caller.msg(self._usage())
                return
            self.caller.msg(f"{getattr(target, 'key', 'Character')}:\n{format_trainer_xp_status(target)}")
            return

        if not self.amount_expr:
            self.caller.msg(self._usage())
            return
        try:
            amount = int(self.amount_expr)
        except (TypeError, ValueError):
            self.caller.msg("Amount must be a whole number.")
            return

        if self.action == "set":
            if amount < 0:
                self.caller.msg("TXP cannot be set below zero.")
                return
            new_total = set_trainer_xp(target, amount)
            verb = "set"
        else:
            current = get_trainer_xp(target)
            new_total = set_trainer_xp(target, current + amount)
            verb = "adjusted"

        level = trainer_level_for_xp(new_total)
        self.caller.msg(
            f"{getattr(target, 'key', 'Character')} TXP {verb} to {new_total:,} "
            f"(trainer level {level})."
        )
