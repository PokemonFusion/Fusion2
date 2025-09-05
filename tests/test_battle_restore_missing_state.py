"""Test restoring battle state reconstructs missing teams and movesets."""

import types

from .test_battle_rebuild import BattleSession, DummyRoom


class DummyPokemonModel:
    """Simple stand-in for a stored Pokémon model."""

    def __init__(self, name: str):
        self.name = name
        self.level = 5
        self.moves = ["tackle"]
        self.current_hp = 20
        # Use an object with an empty string representation so ``model_id``
        # serialises as empty and moves are persisted.
        self.unique_id = type("NoID", (), {"__str__": lambda self: ""})()


class DummyStorage:
    """Storage container returning a predefined party."""

    def __init__(self, party):
        self.party = party

    def get_party(self):  # pragma: no cover - trivial
        return list(self.party)


class DummyPlayer:
    """Player with a configurable Pokémon party."""

    def __init__(self, pid: int, room: DummyRoom, party):
        self.key = f"Player{pid}"
        self.id = pid
        self.db = types.SimpleNamespace()
        self.ndb = types.SimpleNamespace()
        self.location = room
        self.storage = DummyStorage(party)

    def msg(self, text):  # pragma: no cover - interface stub
        pass


def test_restore_rebuilds_missing_movesets_and_teams():
    """Persist a compact state lacking movesets/teams and ensure restore rebuilds them."""

    room = DummyRoom()
    poke_a = DummyPokemonModel("Alpha")
    poke_b = DummyPokemonModel("Bravo")
    p1 = DummyPlayer(1, room, [poke_a])
    p2 = DummyPlayer(2, room, [poke_b])

    inst = BattleSession(p1, p2)
    inst.start_pvp()

    # Persist a compacted state without movesets or teams
    compact_state = inst._compact_state_for_persist(inst.state.to_dict())
    assert "movesets" not in compact_state and "teams" not in compact_state
    inst.storage.set("state", compact_state)

    # Simulate a reload of the session
    room.ndb.battle_instances = {}
    restored = BattleSession.restore(room, inst.battle_id)
    assert restored is not None

    # Restored state should rebuild movesets and teams
    assert restored.state.movesets
    assert restored.state.teams["A"]
    assert restored.state.teams["B"]
    for ms in restored.state.movesets.values():
        assert "tackle" in [name.lower() for name in ms.values()]
