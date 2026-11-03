import contextlib
import types

import pytest

from pokemon.adventures import progress


@pytest.fixture(autouse=True)
def fake_player_lock(monkeypatch):
    """Use in-memory objects for these service tests; ORM coverage is separate."""

    monkeypatch.setattr(progress, "_lock_player", lambda _player: None)


class FakeParticipation:
    _next_pk = 1

    def __init__(self, session, player):
        self.pk = FakeParticipation._next_pk
        FakeParticipation._next_pk += 1
        self.session = session
        self.player = player
        self.route_key = ""
        self.outcome_key = ""
        self.encounter_result = ""
        self.completed_at = None
        self.reward_item = ""
        self.reward_amount = 0
        self.reward_claimed_at = None

    def save(self, update_fields=None):
        self.saved_fields = update_fields


class FakeQuery:
    def __init__(self, rows):
        self.rows = list(rows)

    def exclude(self, **kwargs):
        return FakeQuery(
            row for row in self.rows if any(getattr(row, key) != value for key, value in kwargs.items())
        )

    def exists(self):
        return bool(self.rows)


class FakeManager:
    def __init__(self):
        self.rows = []

    def get_or_create(self, *, session, player):
        for row in self.rows:
            if row.session is session and row.player is player:
                return row, False
        row = FakeParticipation(session, player)
        self.rows.append(row)
        return row, True

    def select_for_update(self):
        return self

    def get(self, *, session, player):
        return next(row for row in self.rows if row.session is session and row.player is player)

    def filter(self, **kwargs):
        rows = self.rows
        for key, value in kwargs.items():
            if key == "session__template_key":
                rows = [row for row in rows if row.session.template_key == value]
            elif key == "completed_at__isnull":
                rows = [row for row in rows if (row.completed_at is None) == value]
            else:
                rows = [row for row in rows if getattr(row, key) is value]
        return FakeQuery(rows)


def test_first_clear_reward_is_claimed_once(monkeypatch):
    manager = FakeManager()
    model = types.SimpleNamespace(objects=manager)
    monkeypatch.setattr(progress, "_model", lambda: model)
    monkeypatch.setattr(progress.transaction, "atomic", contextlib.nullcontext)
    inventory = []
    player = types.SimpleNamespace(
        trainer=types.SimpleNamespace(add_item=lambda item, amount: inventory.append((item, amount)))
    )
    session = types.SimpleNamespace(template_key="alpha_meadow", leader=player, state="completed")
    manager.get_or_create(session=session, player=player)

    first = progress.finalize_completion(session)
    second = progress.finalize_completion(session)

    assert first == (True, "First-clear reward: Potion x1.")
    assert second == (False, "")
    assert inventory == [("Potion", 1)]


def test_failed_inventory_delivery_leaves_reward_claimable(monkeypatch):
    manager = FakeManager()
    model = types.SimpleNamespace(objects=manager)
    monkeypatch.setattr(progress, "_model", lambda: model)
    monkeypatch.setattr(progress.transaction, "atomic", contextlib.nullcontext)
    player = types.SimpleNamespace(trainer=types.SimpleNamespace(add_item=lambda *_args: (_ for _ in ()).throw(RuntimeError())))
    session = types.SimpleNamespace(template_key="alpha_meadow", leader=player, state="completed")
    participation, _created = manager.get_or_create(session=session, player=player)

    claimed, message = progress.finalize_completion(session)

    assert not claimed
    assert "remains unclaimed" in message
    assert participation.reward_item == "Potion"
    assert participation.reward_claimed_at is None

    inventory = []
    player.trainer.add_item = lambda item, amount: inventory.append((item, amount))
    assert progress.finalize_completion(session)[0]
    assert not progress.finalize_completion(session)[0]
    assert inventory == [("Potion", 1)]


def test_claim_recovers_missing_participation_after_leaving(monkeypatch):
    """A completed run can be claimed without a current-session pointer."""

    from pokemon.adventures import sessions

    manager = FakeManager()
    monkeypatch.setattr(progress, "_model", lambda: types.SimpleNamespace(objects=manager))
    monkeypatch.setattr(progress.transaction, "atomic", contextlib.nullcontext)
    inventory = []
    player = types.SimpleNamespace(trainer=types.SimpleNamespace(add_item=lambda *item: inventory.append(item)))
    completed = types.SimpleNamespace(template_key="alpha_meadow", leader=player, state="completed")
    later = types.SimpleNamespace(template_key="alpha_meadow", leader=player, state="completed")

    def completed_runs(**filters):
        assert filters == {"leader": player, "state": "completed"}
        return types.SimpleNamespace(order_by=lambda *_fields: [completed, later])

    monkeypatch.setattr(sessions, "_session_model", lambda: types.SimpleNamespace(
        objects=types.SimpleNamespace(filter=completed_runs)
    ))
    assert "Potion x1" in progress.claim_completed_rewards(player)
    assert progress.claim_completed_rewards(player) == "No unclaimed Adventure rewards."
    assert inventory == [("Potion", 1)]


def test_unfinished_session_cannot_grant_completion_reward():
    """Claim eligibility comes from completed runs, not a caller-supplied ID."""

    player = types.SimpleNamespace()
    session = types.SimpleNamespace(template_key="alpha_meadow", leader=player, state="active")
    assert progress.finalize_completion(session) == (False, "")
