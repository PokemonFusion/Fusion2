"""Test restoring battle state reconstructs missing teams and movesets."""

import types

from utils.pokemon_utils import build_battle_pokemon_from_model

from .test_battle_rebuild import BattleSession, DummyRoom, bi_mod


class DummyPokemonModel:
    """Simple stand-in for a stored Pokémon model."""

    def __init__(self, name: str, moves=None):
        self.name = name
        self.level = 5
        self.moves = list(moves or ["tackle"])
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


def test_restore_rehydrates_wild_moves_from_state():
    """Ensure wild encounters regain their moves when restored."""

    room = DummyRoom()
    trainer_poke = DummyPokemonModel("Alpha", moves=["Quick Attack", "Growl"])
    player = DummyPlayer(1, room, [trainer_poke])

    wild_template = DummyPokemonModel(
        "Zapling", moves=["Thunderbolt", "Quick Attack", "Swift", "Tail Whip"]
    )
    inst = BattleSession(player)
    inst._select_opponent = lambda: (
        build_battle_pokemon_from_model(wild_template),
        "Wild",
        bi_mod.BattleType.WILD,
        "A wild Zapling appears!",
    )
    inst.start()

    stored_data = inst.storage.get("data")
    foe_entry = stored_data["teams"]["B"]["pokemon"][0]
    expected_moves = [m["name"] for m in foe_entry.get("moves", [])]
    assert expected_moves, "wild Pokémon should start with moves"

    foe_entry["moves"] = []
    pos_entry = stored_data.get("turndata", {}).get("B1", {}).get("pokemon")
    if pos_entry:
        pos_entry["moves"] = []
    inst.storage.set("data", stored_data)

    player.ndb.battle_instance = None
    room.ndb.battle_instances = {}

    restored = BattleSession.restore(room, inst.battle_id)
    assert restored is not None

    foe = restored.logic.data.teams["B"].returnlist()[0]
    restored_moves = [mv.name for mv in getattr(foe, "moves", [])]
    expected_lower = [name.lower() for name in expected_moves]
    restored_lower = [name.lower() for name in restored_moves]

    assert len(restored_lower) >= len(expected_lower)
    assert restored_lower[: len(expected_lower)] == expected_lower
    assert any(
        [name.lower() for name in moveset.values()] == expected_lower
        for moveset in restored.state.movesets.values()
    )
