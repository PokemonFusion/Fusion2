"""Center healing must not mutate Pokémon behind an active battle."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize("lock,runtime", [(7, None), (None, object()), (0, None)])
def test_center_healing_is_blocked_during_battle(monkeypatch, lock, runtime):
    """Both durable locks and live sessions prevent HP, status and PP writes."""
    evennia = ModuleType("evennia")
    evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", evennia)
    path = Path(__file__).resolve().parents[2] / "commands/debug/command.py"
    spec = importlib.util.spec_from_file_location("qa_heal_command", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pokemon = SimpleNamespace(heal=Mock())
    caller = SimpleNamespace(
        db=SimpleNamespace(battle_lock=lock), ndb=SimpleNamespace(battle_instance=runtime),
        location=SimpleNamespace(db=SimpleNamespace(is_pokemon_center=True)),
        storage=SimpleNamespace(get_party=lambda: [pokemon]), msg=Mock(),
    )
    command = module.CmdHeal()
    command.caller = caller
    command.func()
    pokemon.heal.assert_not_called()
    caller.msg.assert_called_once_with("You cannot do that during battle.")
