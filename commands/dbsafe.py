"""
Database-safe command base for PF2.

Evennia is a long-running process, so Django DB connections can become stale
between player commands after idle periods. Refresh old/unusable connections
around command execution so the ORM can reconnect cleanly.
"""

from django.db import close_old_connections

from evennia.commands.default.muxcommand import MuxCommand


class DBSafeMuxCommand(MuxCommand):
    """
    MuxCommand wrapper that clears stale Django DB connections.

    This is intentionally silent and should not produce player-facing output.
    """

    def at_pre_cmd(self):
        close_old_connections()
        return super().at_pre_cmd()

    def at_post_cmd(self):
        try:
            return super().at_post_cmd()
        finally:
            close_old_connections()
