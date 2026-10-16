"""Gym victory retry and cleanup guards at the battle-session boundary."""

from types import SimpleNamespace

import pytest

from pokemon.battle.battleinstance import BattleSession
from pokemon.services.gym_rewards import GymClaimResult, GymVictoryRewards


class ResultStorage:
    """Retain battle result snapshots and optionally fail the handled marker."""

    def __init__(self):
        self.values = {}
        self.fail_handled = False

    def set(self, key, value):
        if self.fail_handled and value.get("handled"):
            raise RuntimeError("handled marker unavailable")
        self.values[key] = dict(value)


def battle_session():
    """Build only the session state used by result dispatch and cleanup guards."""
    player = SimpleNamespace(pk=71, id=71)
    session = object.__new__(BattleSession)
    session.teamA = [player]
    session.teamB = []
    session.logic = SimpleNamespace(battle=object())
    session.encounter_metadata = {"source_type": "gym_leader", "badge_id": 21}
    session._battle_result_handled = False
    session.storage = ResultStorage()
    session.messages = []
    session.msg = session.messages.append
    return session


@pytest.mark.parametrize("failure", ["exception", "unresolved"])
def test_saved_gym_victory_retries_without_original_winner(monkeypatch, failure):
    """Neither an exception nor an unresolved award consumes the victory."""
    session = battle_session()
    records = {}
    claims = []

    def record(rewards, victory_id, metadata):
        assert session.storage.values["battle_result"]["handled"] is False
        records.setdefault(victory_id, (rewards.player, dict(metadata)))

    def claim(rewards, victory_id):
        assert victory_id in records
        claims.append(victory_id)
        if len(claims) == 1:
            if failure == "exception":
                raise RuntimeError("badge delivery failed")
            return GymClaimResult(False, "Badge unavailable. Use +gym claim.")
        return GymClaimResult(True, "You earned the badge!", awarded=True)

    monkeypatch.setattr(GymVictoryRewards, "record", record)
    monkeypatch.setattr(GymVictoryRewards, "claim", claim)
    session._handle_battle_result(SimpleNamespace(team="A", player=session.captainA))
    victory_id = session._gym_victory_id
    assert not session._battle_result_handled
    assert "+gym claim" in session.messages[-1]
    assert records[victory_id] == (session.captainA, session.encounter_metadata)

    session._handle_battle_result(None)
    session._handle_battle_result(None)
    assert session._battle_result_handled
    assert claims == [victory_id, victory_id]
    assert len(records) == 1


def test_gym_cleanup_keeps_battle_when_victory_cannot_be_saved(monkeypatch):
    """Never delete the only copy of a confirmed win during a ledger outage."""
    session = battle_session()

    def fail_record(*args):
        raise RuntimeError("victory ledger unavailable")

    monkeypatch.setattr(GymVictoryRewards, "record", fail_record)
    session._handle_battle_result(SimpleNamespace(team="A", player=session.captainA))
    assert session.storage.values["battle_result"]["result"] == "win"
    assert not session._battle_result_handled
    with pytest.raises(RuntimeError, match="victory ledger unavailable"):
        session.end()
    assert session.logic is not None
    assert session.storage.values["battle_result"]["gym_victory_id"] == session._gym_victory_id


def test_handled_marker_failure_reuses_already_claimed_victory(monkeypatch):
    """A battle marker failure after delivery must not create another award."""
    session = battle_session()
    claimed = set()
    awards = []
    monkeypatch.setattr(GymVictoryRewards, "record", lambda *args: None)

    def claim(rewards, victory_id):
        if victory_id not in claimed:
            awards.append(victory_id)
            claimed.add(victory_id)
        return GymClaimResult(True, "Badge claimed.")

    monkeypatch.setattr(GymVictoryRewards, "claim", claim)
    session.storage.fail_handled = True
    session._handle_battle_result(SimpleNamespace(team="A", player=session.captainA))
    assert not session._battle_result_handled
    session.storage.fail_handled = False
    session._handle_battle_result(None)
    assert session._battle_result_handled
    assert awards == [session._gym_victory_id]


@pytest.mark.parametrize("winner", [None, SimpleNamespace(team="B", player=None)])
def test_nonvictory_does_not_create_gym_entitlement(monkeypatch, winner):
    """Loss, concession, or missing winner cannot create a claim."""
    session = battle_session()
    records = []
    monkeypatch.setattr(GymVictoryRewards, "record", lambda *args: records.append(args))
    session._handle_battle_result(winner)
    assert not records
    assert not getattr(session, "_gym_victory_id", None)
