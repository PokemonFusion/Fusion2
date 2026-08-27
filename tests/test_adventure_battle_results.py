import types

from pokemon.adventures import sessions as adventure_sessions
from pokemon.battle.battleinstance import BattleSession


class FakeStorage:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value


def _battle_session(player, *, capture_count_before=0, fled=False):
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
