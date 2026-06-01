"""Wizard command for controlling active fusion battle boosts."""

from __future__ import annotations

from evennia import Command

from utils.fusion import is_fusion_boost_enabled, set_fusion_boost_enabled


class CmdFusionBoost(Command):
    """View or change whether active fusion forms receive a stat boost.

    Usage:
      @fusionboost
      @fusionboost on
      @fusionboost off
      @fusionboost clear
    """

    key = "@fusionboost"
    aliases = ["fusionboost"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def parse(self):
        """Normalize the requested setting."""

        self.setting = (self.args or "").strip().lower()

    def _show_current(self):
        state = "enabled" if is_fusion_boost_enabled() else "disabled"
        self.caller.msg(f"Fusion battle stat boost is currently {state}.")

    def func(self):
        """Display or update the fusion battle boost setting."""

        if not self.setting:
            self._show_current()
            return

        if self.setting in {"on", "yes", "true", "enabled", "enable"}:
            enabled = set_fusion_boost_enabled(True)
        elif self.setting in {"off", "no", "false", "disabled", "disable"}:
            enabled = set_fusion_boost_enabled(False)
        elif self.setting == "clear":
            enabled = set_fusion_boost_enabled(None)
            state = "enabled" if enabled else "disabled"
            self.caller.msg(f"Fusion battle stat boost override cleared; default is {state}.")
            return
        else:
            self.caller.msg("Usage: @fusionboost [on||off||clear]")
            return

        state = "enabled" if enabled else "disabled"
        self.caller.msg(f"Fusion battle stat boost {state}.")
