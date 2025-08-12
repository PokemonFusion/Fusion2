import pytest

from pokemon.battle.battleinstance import BattleSession


class Dummy:
    """Simple stand-in for a player object collecting received messages."""

    def __init__(self, key: str):
        self.key = key
        self.received: list[str] = []

    def msg(self, text: str) -> None:
        self.received.append(text)


def _make_session():
    inst = object.__new__(BattleSession)
    player = Dummy("Ash")
    opponent = Dummy("Gary")
    inst.teamA = []
    inst.teamB = []
    inst.trainers = []
    inst.observers = set()
    inst.captainA = player
    inst.captainB = opponent
    inst.trainers = [player, opponent]
    return inst, player, opponent


def test_msg_prefix():
    inst, p1, p2 = _make_session()
    inst.msg("Ready?")
    expected = "[Battle: Ash vs. Gary] Ready?"
    assert p1.received[-1] == expected
    assert p2.received[-1] == expected


def test_msg_to_prefix():
    inst, p1, p2 = _make_session()
    watcher = Dummy("Brock")
    inst._msg_to(watcher, "Hello")
    expected = "[Battle: Ash vs. Gary] Hello"
    assert watcher.received[-1] == expected
