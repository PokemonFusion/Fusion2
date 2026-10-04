"""Held item command parsing; persistence/rollback tests use the real ORM."""

from unittest.mock import Mock

import pytest

from tests.test_evolve_command_safety import load_command


@pytest.mark.parametrize("args,item", [("1=Oran Berry", "Oran Berry"), ("1=", None)])
def test_hold_full_item_name_and_removal(monkeypatch, args, item):
    module, service, _ = load_command(monkeypatch, "cmd_party.py")
    command = module.CmdSetHoldItem()
    command.caller, command.args = Mock(), args
    service.hold.return_value = "Completed."
    command.func()
    service.hold.assert_called_once_with(1, item)
    command.caller.msg.assert_called_once_with("Completed.")


def test_hold_surfaces_service_validation(monkeypatch):
    module, service, error = load_command(monkeypatch, "cmd_party.py")
    service.hold.side_effect = error("Use a complete item name.")
    command = module.CmdSetHoldItem()
    command.caller, command.args = Mock(), "1=Oran"
    command.func()
    command.caller.msg.assert_called_once_with("Use a complete item name.")


@pytest.mark.parametrize("args", ["1", "not-a-slot=Oran Berry"])
def test_hold_rejects_invalid_syntax(monkeypatch, args):
    module, service, _ = load_command(monkeypatch, "cmd_party.py")
    command = module.CmdSetHoldItem()
    command.caller, command.args = Mock(), args
    command.func()
    service.hold.assert_not_called()
