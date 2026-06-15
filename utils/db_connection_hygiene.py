"""Django database connection hygiene for long-lived Evennia workers."""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def close_stale_connections() -> None:
    """Reset Django's connection health state and close obsolete connections."""

    try:
        from django.db import close_old_connections
    except Exception:  # pragma: no cover - Django may be stubbed in import-only tests
        return

    try:
        close_old_connections()
    except Exception:
        logger.exception("Failed while closing old Django database connections.")


def _patch_command_class(command_cls: type[Any]) -> None:
    """Wrap an Evennia command class's boundary hooks once."""

    if getattr(command_cls, "_pf2_db_connection_hygiene_installed", False):
        return

    original_pre = command_cls.at_pre_cmd
    original_post = command_cls.at_post_cmd

    @wraps(original_pre)
    def at_pre_cmd(self: Any, *args: Any, **kwargs: Any) -> Any:
        close_stale_connections()
        return original_pre(self, *args, **kwargs)

    @wraps(original_post)
    def at_post_cmd(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return original_post(self, *args, **kwargs)
        finally:
            close_stale_connections()

    command_cls.at_pre_cmd = at_pre_cmd
    command_cls.at_post_cmd = at_post_cmd
    command_cls._pf2_db_connection_hygiene_installed = True


def install_command_connection_hygiene() -> None:
    """Install command-boundary DB cleanup for Evennia command bases."""

    try:
        from evennia.commands.command import Command
        from evennia.commands.default.muxcommand import MuxCommand
    except Exception:  # pragma: no cover - Evennia may be unavailable in unit stubs
        return

    for command_cls in (Command, MuxCommand):
        _patch_command_class(command_cls)
