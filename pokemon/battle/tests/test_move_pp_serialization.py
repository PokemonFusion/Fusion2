"""Tests ensuring move PP values survive battle data serialisation."""

import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

from pokemon.battle.battledata import Move, Pokemon


class _SlotManager(list):
        """Lightweight helper mimicking an ``ActiveMoveSlot`` queryset."""

        def all(self):
                return self


class _Slot:
        """Stub move slot storing the current PP for a move."""

        def __init__(self, move_name: str, slot: int, current_pp: int):
                self.move = types.SimpleNamespace(name=move_name)
                self.slot = slot
                self.current_pp = current_pp


def test_move_pp_survives_serialisation_roundtrip():
        """Serialising and loading a Pokémon should preserve move PP values."""

        moves = [Move(name="Quick Attack"), Move(name="Tackle")]
        moves[0].pp = 12

        mon = Pokemon(name="Eevee", level=5, hp=20, moves=moves)
        mon.activemoveslot_set = _SlotManager([
                _Slot("Quick Attack", 1, 12),
                _Slot("Tackle", 2, 7),
        ])

        payload = mon.to_dict()
        assert payload["moves"][0]["pp"] == 12
        assert payload["moves"][1]["pp"] == 7

        restored = Pokemon.from_dict(payload)
        restored_pp = [getattr(move, "pp", None) for move in restored.moves]
        assert restored_pp == [12, 7]
