"""Tests debug logging for a full PvP turn."""

from tests.test_battle_rebuild import BattleSession, DummyRoom, DummyPlayer
from pokemon.battle.engine import _apply_move_damage, BattleMove


class StoredPoke:
    """Minimal stored Pokémon model used for battle setup."""

    def __init__(self, uid: str) -> None:
        self.name = "Bulbasaur"
        self.level = 5
        self.moves = ["tackle"]
        self.current_hp = 20
        self.unique_id = uid


class StorageWithPoke:
    """Storage stub returning a single Pokémon."""

    def __init__(self, uid: str) -> None:
        self.poke = StoredPoke(uid)

    def get_party(self):
        """Return the stored party list."""
        return [self.poke]


def test_pvp_turn_debug_logging(monkeypatch):
    """A queued turn records debug information when debug mode is active."""

    room = DummyRoom()
    p1 = DummyPlayer(1, room)
    p1.storage = StorageWithPoke("uid1")
    p2 = DummyPlayer(2, room)
    p2.storage = StorageWithPoke("uid2")
    inst = BattleSession(p1, p2)
    inst.start_pvp()

    inst.battle.debug = True
    logs: list[str] = []
    inst.battle.log_action = logs.append

    # Avoid the automatic turn resolution so we can inspect the queued state.
    monkeypatch.setattr(inst, "maybe_run_turn", lambda: None)

    inst.queue_move("tackle", caller=p1)
    inst.queue_move("tackle", caller=p2)

    assert inst.battle.turn_count == 1

    user = inst.battle.participants[0].active[0]
    target = inst.battle.participants[1].active[0]
    move = BattleMove(name="tackle", power=40, accuracy=100, type="Normal", raw={"category": "Physical"})
    _apply_move_damage(user, target, move, inst.battle)

    debug_lines = [msg for msg in logs if "[DEBUG]" in msg]
    assert any("atk=" in line and "dmg=" in line for line in debug_lines)
