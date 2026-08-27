import contextlib
import types

from pokemon.adventures import progress


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
    session = types.SimpleNamespace(template_key="alpha_meadow", leader=player)
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
    session = types.SimpleNamespace(template_key="alpha_meadow", leader=player)
    participation, _created = manager.get_or_create(session=session, player=player)

    claimed, message = progress.finalize_completion(session)

    assert not claimed
    assert "remains unclaimed" in message
    assert participation.reward_item == "Potion"
    assert participation.reward_claimed_at is None
