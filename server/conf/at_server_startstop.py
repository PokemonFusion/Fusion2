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

from utils.error_logging import setup_daily_error_log
from utils.usage_logging import setup_daily_usage_log
from utils.battle_logging import setup_daily_battle_log


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    Configure the daily error log handler.
    """
    base_dir = Path(__file__).resolve().parents[1]
    log_dir = base_dir / "logs"
    setup_daily_error_log(log_dir)
    setup_daily_usage_log(log_dir)
    setup_daily_battle_log(log_dir)


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    from pokemon.battle.handler import battle_handler
    battle_handler.restore()
    battle_handler.rebuild_ndb()


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    from pokemon.battle.handler import battle_handler
    battle_handler.save()
    # Avoid calling logging.shutdown() here because Evennia and Twisted manage
    # their own logging shutdown. Forcing it can lead to "I/O operation on
    # closed file" errors if any component tries to log during shutdown.


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.

    We must restore and repopulate ``ndb`` attributes here so that any
    active battles continue to work immediately after the server
    reloads.  This mirrors the initialization done in ``at_server_start``.
    """
    from pokemon.battle.handler import battle_handler

    # Recreate active instances from persistent storage and then rebuild
    # their non-persistent references.
    battle_handler.restore()
    battle_handler.rebuild_ndb()


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
    from pokemon.battle.handler import battle_handler

    # Recreate any saved battle instances since non-persistent
    # attributes were wiped as part of the shutdown.
    battle_handler.restore()
    battle_handler.rebuild_ndb()


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    from pokemon.battle.handler import battle_handler
    battle_handler.save()
    # Do not call logging.shutdown() — Evennia/Twisted handles this safely
