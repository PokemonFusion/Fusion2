from __future__ import annotations

from evennia import Command

from menus import chargen as chargen_menu
from utils.enhanced_evmenu import EnhancedEvMenu


class CmdChargen(Command):
    """Interactive character creation.

    Usage:
      chargen

    Examples:
      chargen

    Notes:
      Beta setup is self-service. Accepted choices resume after reconnect; completion grants one starter or initial Fusion once.
    """

    key = "chargen"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        from pokemon.services.onboarding import Onboarding, OnboardingError

        service = Onboarding(self.caller)
        if service.completion() or self.caller.db.chargen_completed or self.caller.db.validated:
            self.caller.msg("Your character setup is already complete. No additional starter or form can be granted. Use +sheet and help getting started.")
            return
        try:
            node, kwargs = service.resume()
        except OnboardingError as error:
            self.caller.msg(str(error))
            return
        self.caller.msg("Beta setup is self-service; no staff validation is required. Your accepted choices are saved until completion.")
        EnhancedEvMenu(
            self.caller,
            chargen_menu,
            startnode=node,
            startnode_input=("", kwargs),
            cmd_on_exit=None,
            on_abort=lambda caller: caller.msg("Character setup paused. Use chargen to resume your saved choices."),
            numbered_options=False,
            show_options=False,
        )
