"""Check exit merging with real Evennia commands, using only SQLite memory."""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

from django.conf import settings

settings.DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
}

import django
from django.db.backends.base.base import BaseDatabaseWrapper

_connect = BaseDatabaseWrapper.connect


def connect_memory_only(connection):
    """Reject any attempt to connect to the game's database."""
    assert connection.vendor == "sqlite", connection.vendor
    assert connection.settings_dict["NAME"] == ":memory:"
    return _connect(connection)


def check_exit_commands():
    """Exercise production exit commands through Evennia's merge and parser."""
    from evennia.commands.cmdparser import cmdparser
    from evennia.commands.cmdset import CmdSet
    from evennia.commands.command import Command
    from evennia.commands.default.general import CmdLook
    from evennia.objects.objects import SIGNAL_EXIT_TRAVERSED

    from typeclasses.exits import Exit

    def make_exit(key, aliases):
        """Supply exit data and traversal hooks without saving a world object."""
        return SimpleNamespace(
            db_key=key,
            aliases=SimpleNamespace(all=lambda: aliases),
            locks="cmd:all();traverse:all()",
            db_destination=destination,
            destination=destination,
            db=SimpleNamespace(err_traverse=None),
            access=Mock(return_value=True),
            at_traverse=Mock(),
            at_failed_traverse=Mock(),
        )

    destination = object()
    caller = SimpleNamespace(msg=Mock())
    exit_type = Exit()
    grass = make_exit("(L)ow (G)rass", ["l", "lg", "low grass", "route1", "w", "west"])
    exits = exit_type.create_exit_cmdset(grass)
    core = CmdSet()
    look = CmdLook()
    core.add(look)
    merged = exits + core

    for name in ["(L)ow (G)rass", "lg", "low grass", "route1", "w", "west"]:
        matches = cmdparser(name, merged, caller)
        assert len(matches) == 1, (name, matches)
        command = matches[0][2]
        assert command.is_exit and command.obj is grass, name
        assert command.destination is destination, name
        assert not command.auto_help, name
    for name in ["l", "look", "ls"]:
        assert cmdparser(name, merged, caller)[0][2] is look, name
    assert not cmdparser("low grass extra", merged, caller)

    # Other collisions must also remove only the conflicting traversal name.
    core.add(Command(key="route1", locks="cmd:all()"))
    merged = exits + core
    assert not cmdparser("route1", merged, caller)[0][2].is_exit
    assert cmdparser("low grass", merged, caller)[0][2].obj is grass

    # Equal-priority exits sharing a direction remain ambiguous to the player.
    gym = make_exit("alpha gym", ["s", "south"])
    meadow = make_exit("capture meadow", ["s", "south"])
    merged = exit_type.create_exit_cmdset(gym) + exit_type.create_exit_cmdset(meadow) + core
    assert len(cmdparser("south", merged, caller)) == 2
    assert cmdparser("alpha gym", merged, caller)[0][2].obj is gym
    assert cmdparser("capture meadow", merged, caller)[0][2].obj is meadow

    # Case-equivalent aliases on one exit must not create an ambiguous match.
    repeated = make_exit("OUT", ["out", "Out", " OUT "])
    assert len(cmdparser("out", exit_type.create_exit_cmdset(repeated), caller)) == 1

    command = cmdparser("low grass", exits + core, caller)[0][2]
    command.caller = caller
    with patch.object(SIGNAL_EXIT_TRAVERSED, "send") as signal:
        command.func()
        grass.at_traverse.assert_called_once_with(caller, destination)
        signal.assert_called_once_with(sender=grass, traverser=caller)
        grass.access.return_value = False
        command.func()
        grass.at_traverse.assert_called_once()
        grass.at_failed_traverse.assert_called_once_with(caller)
        signal.assert_called_once()


with patch("django.db.backends.base.base.BaseDatabaseWrapper.connect", connect_memory_only):
    django.setup()
    check_exit_commands()

print("Real Evennia exit command checks passed; only SQLite memory was used.")
