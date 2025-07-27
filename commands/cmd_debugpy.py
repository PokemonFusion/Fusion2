from __future__ import annotations

import sys
import logging

from django.conf import settings
from evennia.utils import utils

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)

ERROR_MSG = (
    "Error, debugpy not found! Please install debugpy by running: `pip install debugpy`"
    "\nAfter that please reboot Evennia with `evennia reboot`"
)

try:  # pragma: no cover - optional debugpy dependency
    import debugpy  # type: ignore
except ImportError:  # pragma: no cover - import-time check
    debugpy = None  # type: ignore


class CmdDebugPy(COMMAND_DEFAULT_CLASS):
    """Launch the debugpy debugger and wait for attach on port 5678.

    Usage:
      @debugpy
    """

    key = "@debugpy"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if debugpy is None:
            self.caller.msg(ERROR_MSG)
            return

        caller = self.caller
        caller.msg("Waiting for debugger attach...")
        yield 0.1  # ensure message is sent before blocking
        host, port = debugpy.listen(5678)
        debugpy.wait_for_client()
        caller.msg("Debugger attached.")
        logging.getLogger(__name__).info(
            "debugpy debugger connected on %s:%d", host, port
        )
