"""Tests for the +showbattle command."""

from commands.player.cmd_showbattle import CmdShowBattle
from pokemon.battle.battleinstance import BattleSession


class Dummy:
    """Minimal object storing received messages."""

    def __init__(self, key: str):
        self.key = key
        self.received = []
        self.ndb = type("NDB", (), {})()

    def msg(self, text: str) -> None:
        self.received.append(text)


def _make_session():
    inst = object.__new__(BattleSession)
    p1 = Dummy("Red")
    p2 = Dummy("Blue")
    inst.teamA = [p1]
    inst.teamB = [p2]
    inst.captainA = p1
    inst.captainB = p2
    inst.logic = type("Logic", (), {"state": object()})()
    p1.ndb.battle_instance = inst
    p2.ndb.battle_instance = inst
    return inst, p1, p2

def test_showbattle_self(monkeypatch):
    inst, p1, _ = _make_session()
    monkeypatch.setattr(
        "commands.player.cmd_showbattle.display_battle_interface",
        lambda *a, **k: "UI",
    )
    cmd = CmdShowBattle()
    cmd.caller = p1
    cmd.args = ""
    cmd.func()
    assert p1.received[-1] == "UI"


def test_showbattle_target(monkeypatch):
    inst, p1, _ = _make_session()
    viewer = Dummy("Viewer")
    monkeypatch.setattr(
        "commands.player.cmd_showbattle.display_battle_interface",
        lambda *a, **k: "UI",
    )
    monkeypatch.setattr(
        "commands.player.cmd_showbattle.search_object",
        lambda name: [p1] if name == "Red" else [],
    )
    cmd = CmdShowBattle()
    cmd.caller = viewer
    cmd.args = "Red"
    cmd.func()
    assert viewer.received[-1] == "UI"
