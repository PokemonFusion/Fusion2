"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""

from pathlib import Path
import logging

from utils.error_logging import setup_daily_error_log
from utils.usage_logging import setup_daily_usage_log
from utils.logging_patch import patch_open_log_file


def _flush_logging_handlers() -> None:
    """Flush all handlers attached to configured loggers."""
    for logger in [logging.getLogger(name) for name in logging.root.manager.loggerDict.keys()] + [logging.getLogger()]:
        for handler in getattr(logger, "handlers", []):
            try:
                handler.flush()
            except Exception:
                pass


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    Configure the daily error log handler.
    """
    base_dir = Path(__file__).resolve().parents[1]
    log_dir = base_dir / "logs"
    setup_daily_error_log(log_dir)
    setup_daily_usage_log(log_dir)
    # ensure evennia log files reopen properly after shutdown
    patch_open_log_file()


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    from pokemon.battle.handler import battle_handler
    battle_handler.restore()


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    from pokemon.battle.handler import battle_handler
    battle_handler.save()
    # flush logging handlers to ensure log buffers are written without closing
    _flush_logging_handlers()


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    pass


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    pass


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    pass


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    from pokemon.battle.handler import battle_handler
    battle_handler.save()
    # ensure log files are flushed when the server fully stops without closing
    _flush_logging_handlers()
