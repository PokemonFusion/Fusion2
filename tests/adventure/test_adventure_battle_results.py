import types

import pytest

from pokemon.adventures import sessions as adventure_sessions
from pokemon.battle.battleinstance import BattleSession


class FakeStorage:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value


def _battle_session(player, *, capture_count_before=0, fled=False):
    player.db = types.SimpleNamespace()
    battle = object.__new__(BattleSession)
    battle.teamA = [player]
    battle.teamB = []
    battle.logic = types.SimpleNamespace(
        battle=types.SimpleNamespace(_flee_result={"success": fled} if fled else {}),
    )
    battle.encounter_metadata = {
        "source_type": "adventure",
        "adventure_session_id": 17,
        "capture_count_before": capture_count_before,
    }
    battle._battle_result_handled = False
    battle.storage = FakeStorage()
    battle.msg = lambda _message: None
    return battle


def test_adventure_battle_result_dispatches_once(monkeypatch):
    player = types.SimpleNamespace(ndb=types.SimpleNamespace(pending_caught_pokemon=[]))
    battle = _battle_session(player)
    calls = []
    monkeypatch.setattr(
        adventure_sessions,
        "resolve_encounter_result",
        lambda session_id, caller, result: calls.append((session_id, caller, result))
        or adventure_sessions.AdventureActionResult(True, "resolved"),
    )

    winner = types.SimpleNamespace(team="A", player=player)
    battle._handle_battle_result(winner)
    battle._handle_battle_result(winner)

    assert calls == [(17, player, "win")]
    assert battle.storage.values["battle_result"] == {"handled": True, "result": "win"}


def test_adventure_battle_result_distinguishes_capture_and_flee(monkeypatch):
    calls = []
    monkeypatch.setattr(
        adventure_sessions,
        "resolve_encounter_result",
        lambda _session_id, _caller, result: calls.append(result)
        or adventure_sessions.AdventureActionResult(True, "resolved"),
    )
    player = types.SimpleNamespace(
        ndb=types.SimpleNamespace(pending_caught_pokemon=[{"species": "Rattata"}])
    )
    captured = _battle_session(player, capture_count_before=0)
    captured._handle_battle_result(types.SimpleNamespace(team="A", player=player))

    fled = _battle_session(player, capture_count_before=1, fled=True)
    fled._handle_battle_result(None)

    assert calls == ["capture", "flee"]


@pytest.mark.parametrize("failure", ["exception", "rejected"])
def test_failed_result_is_retryable_with_original_outcome(monkeypatch, failure):
    """Neither a thrown save nor an unsuccessful result consumes the outcome."""

    player = types.SimpleNamespace(ndb=types.SimpleNamespace(pending_caught_pokemon=[]))
    battle = _battle_session(player)
    calls = []

    def resolve(_session_id, _caller, result):
        calls.append(result)
        if len(calls) == 1:
            if failure == "exception":
                raise RuntimeError("temporary save failure")
            return adventure_sessions.AdventureActionResult(False, "not saved")
        return adventure_sessions.AdventureActionResult(True, "resolved")

    monkeypatch.setattr(adventure_sessions, "resolve_encounter_result", resolve)
    battle._handle_battle_result(types.SimpleNamespace(team="A", player=player))
    assert not battle._battle_result_handled
    assert battle.storage.values["battle_result"] == {"handled": False, "result": "win"}
    assert player.db.pending_adventure_results == {"17": "win"}

    # A retry after cleanup/concession no longer has the original winner.
    battle._handle_battle_result(None)
    battle._handle_battle_result(None)
    assert calls == ["win", "win"]
    assert battle._battle_result_handled
    assert player.db.pending_adventure_results == {}


def test_cleanup_stops_if_pending_receipt_cannot_be_saved(monkeypatch):
    """Cleanup must not delete the only recoverable copy during a DB outage."""

    player = types.SimpleNamespace(ndb=types.SimpleNamespace(pending_caught_pokemon=[]))
    battle = _battle_session(player)
    battle._adventure_result = "capture"

    def fail_queue(*_args):
        raise RuntimeError("character storage unavailable")

    monkeypatch.setattr(adventure_sessions, "queue_encounter_result", fail_queue)
    with pytest.raises(RuntimeError, match="character storage unavailable"):
        battle.end()
    assert battle.logic is not None
    assert battle._adventure_result == "capture"
