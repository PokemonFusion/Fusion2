"""Command boundary tests; real transaction coverage lives in integration/."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


def load_command(monkeypatch, filename):
    """Load a command with a small Evennia shell and an observable service."""
    evennia = ModuleType("evennia")
    evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", evennia)
    locks = ModuleType("utils.locks")
    locks.require_no_battle_lock = lambda caller: True
    monkeypatch.setitem(sys.modules, "utils.locks", locks)
    suggestions = ModuleType("utils.dex_suggestions")
    suggestions.suggest_name = lambda *args: None
    monkeypatch.setitem(sys.modules, "utils.dex_suggestions", suggestions)
    service_module = ModuleType("pokemon.services.evolution")
    service_module.EvolutionError = type("EvolutionError", (ValueError,), {})
    service = Mock()
    service_module.EvolutionService = Mock(return_value=service)
    monkeypatch.setitem(sys.modules, service_module.__name__, service_module)
    path = Path(__file__).resolve().parents[1] / "commands/player" / filename
    spec = importlib.util.spec_from_file_location("command_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, service, service_module.EvolutionError


@pytest.mark.parametrize(
    "args,item,target",
    [
        ("mon-1 Fire Stone", "Fire Stone", None),
        ("mon-1   Fire Stone = Ninetales", "Fire Stone ", "Ninetales"),
        ("mon-1 = Ivysaur", None, "Ivysaur"),
        ("mon-1", None, None),
    ],
)
def test_evolve_preserves_complete_item_and_target(monkeypatch, args, item, target):
    module, service, _ = load_command(monkeypatch, "cmd_learn_evolve.py")
    pokemon = SimpleNamespace(name="Fluffy")
    caller = Mock()
    caller.get_pokemon_by_id.return_value = pokemon
    service.evolve.return_value = "Ninetales"
    command = module.CmdEvolvePokemon()
    command.caller, command.args = caller, args
    command.func()
    service.evolve.assert_called_once_with(pokemon, item=item, target=target)
    caller.msg.assert_called_once_with("Fluffy evolved into Ninetales!")


def test_evolve_validation_error_and_retry_are_reported(monkeypatch):
    module, service, error = load_command(monkeypatch, "cmd_learn_evolve.py")
    command = module.CmdEvolvePokemon()
    command.caller, command.args = Mock(), "mon-1 Fire Stone"
    service.evolve.side_effect = error("Use a complete item name.")
    command.func()
    command.caller.msg.assert_called_with("Use a complete item name.")
    service.evolve.side_effect = None
    service.evolve.return_value = None
    command.func()
    assert "already completed" in command.caller.msg.call_args.args[0]


@pytest.mark.parametrize("args", ["", "mon-1="])
def test_evolve_rejects_empty_request_or_target(monkeypatch, args):
    module, service, _ = load_command(monkeypatch, "cmd_learn_evolve.py")
    command = module.CmdEvolvePokemon()
    command.caller, command.args = Mock(), args
    command.func()
    service.evolve.assert_not_called()
