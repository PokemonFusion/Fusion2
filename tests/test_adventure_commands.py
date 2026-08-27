import types

from pokemon.adventures import commands
from pokemon.adventures.cmdsets import (
    AdventureMovementCmdSet,
    attach_movement_cmdset,
    detach_movement_cmdset,
)
from pokemon.adventures.sessions import AdventureActionResult


class DummyCmdSet:
    def __init__(self):
        self.added = []
        self.deleted = []

    def has_cmdset(self, *_args, **_kwargs):
        return False

    def add(self, cmdset, persistent=False):
        self.added.append((cmdset, persistent))

    def delete(self, cmdset):
        self.deleted.append(cmdset)


class DummyCaller:
    def __init__(self):
        self.messages = []
        self.cmdset = DummyCmdSet()

    def msg(self, text):
        self.messages.append(text)


def _run_cmd(switches=None, args="", cmdstring="+adventure", parse=False):
    caller = DummyCaller()
    cmd = commands.CmdAdventure()
    cmd.caller = caller
    cmd.args = args
    cmd.cmdstring = cmdstring
    cmd.switches = set(switches or [])
    if parse:
        cmd.parse()
    cmd.func()
    return caller


def test_adventure_list_command_shows_alpha_meadow():
    caller = _run_cmd({"list"})

    assert "Available adventures:" in caller.messages[-1]
    assert "alpha_meadow - Alpha Meadow Survey" in caller.messages[-1]


def test_adventure_list_command_parses_cmdstring_switch():
    caller = _run_cmd(cmdstring="+adventure/list", parse=True)

    assert "Available adventures:" in caller.messages[-1]


def test_adventure_info_command_shows_template_details():
    caller = _run_cmd({"info"}, "alpha_meadow")

    assert "Alpha Meadow Survey" in caller.messages[-1]
    assert "Reach the Old Tree." in caller.messages[-1]


def test_adventure_start_command_attaches_movement_cmdset(monkeypatch):
    fake_session = types.SimpleNamespace(template_key="alpha_meadow")
    captured = {}

    def fake_start(caller, arg):
        captured["caller"] = caller
        captured["arg"] = arg
        return AdventureActionResult(True, "Started Alpha Meadow Survey.", fake_session)

    monkeypatch.setattr(commands, "start_session", fake_start)
    monkeypatch.setattr(commands, "render_session", lambda session: "rendered adventure")

    caller = _run_cmd({"start"}, "alpha_meadow")

    assert captured["caller"] is caller
    assert captured["arg"] == "alpha_meadow"
    assert caller.messages == ["Started Alpha Meadow Survey.", "rendered adventure"]
    assert caller.cmdset.added[-1] == (AdventureMovementCmdSet, False)


def test_adventure_leave_command_detaches_movement_cmdset(monkeypatch):
    monkeypatch.setattr(
        commands,
        "leave_session",
        lambda caller: AdventureActionResult(True, "You leave Alpha Meadow Survey."),
    )

    caller = _run_cmd({"leave"})

    assert caller.messages[-1] == "You leave Alpha Meadow Survey."
    assert caller.cmdset.deleted[-1] is AdventureMovementCmdSet


def test_adventure_choose_starts_authored_encounter(monkeypatch):
    from pokemon.battle import battleinstance

    choice = types.SimpleNamespace(
        species="Rattata",
        level=5,
        encounter_kind="wild",
        opponent_name="",
        key="wild",
        outcome_key="wild_route",
    )
    session = types.SimpleNamespace(pk=42)
    started = {}

    class FakeBattleSession:
        @staticmethod
        def ensure_for_player(_caller):
            return None

        def __init__(self, caller):
            started["caller"] = caller

        def start_adventure_encounter(self, **kwargs):
            started.update(kwargs)

    monkeypatch.setattr(battleinstance, "BattleSession", FakeBattleSession)
    monkeypatch.setattr(
        commands,
        "choose_session_route",
        lambda _caller, _arg: AdventureActionResult(True, "Route chosen.", session, choice),
    )

    caller = _run_cmd({"choose"}, "wild")

    assert caller.messages == ["Route chosen."]
    assert started["caller"] is caller
    assert started["adventure_session_id"] == 42
    assert started["outcome_key"] == "wild_route"


def test_adventure_look_renders_current_completed_session(monkeypatch):
    fake_session = types.SimpleNamespace(template_key="alpha_meadow", state="completed")
    monkeypatch.setattr(commands, "get_current_session_for_player", lambda caller: fake_session)
    monkeypatch.setattr(commands, "render_session", lambda session: "rendered completed adventure")

    caller = _run_cmd({"look"})

    assert caller.messages[-1] == "rendered completed adventure"
    assert caller.cmdset.added[-1] == (AdventureMovementCmdSet, False)


def test_movement_cmdset_attach_and_detach_helpers():
    caller = DummyCaller()

    attach_movement_cmdset(caller)
    detach_movement_cmdset(caller)

    assert caller.cmdset.added == [(AdventureMovementCmdSet, False)]
    assert caller.cmdset.deleted == [AdventureMovementCmdSet]
