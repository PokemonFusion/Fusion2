from __future__ import annotations

import sys

from django.conf import settings
from evennia.utils import utils

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)

ERROR_MSG = (
    "Error, debugpy not found! Please install debugpy by running: `pip install debugpy`"
    "\nAfter that please reboot Evennia with `evennia reboot`"
)

try:
    import debugpy  # type: ignore
except ImportError:  # pragma: no cover - import-time check
    print(ERROR_MSG)
    sys.exit()


class CmdDebugPy(COMMAND_DEFAULT_CLASS):
    """Launch the debugpy debugger and wait for attach on port 5678.

    Usage:
      @debugpy
    """

    key = "@debugpy"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        caller.msg("Waiting for debugger attach...")
        yield 0.1  # ensure message is sent before blocking
        debugpy.listen(5678)
        debugpy.wait_for_client()
        caller.msg("Debugger attached.")
