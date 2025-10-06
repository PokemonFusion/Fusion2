"""Tests for AI move selection populating PP from MOVEDEX."""

from __future__ import annotations

import random
import types

import pytest


@pytest.mark.parametrize("source_attr", ["pp", "raw_only"])
def test_select_ai_action_assigns_pp_from_movedex(source_attr):
    """Ensure AI-selected moves inherit PP values from the MOVEDEX entry."""

    from pokemon.battle import engine
    from pokemon.battle._shared import _normalize_key, get_pp

    move_name = "Acid"
    key = _normalize_key(move_name)
    original_entry = engine.MOVEDEX.get(key)

    try:
        if source_attr == "pp":
            fake_entry = types.SimpleNamespace(pp=25, raw={"priority": 1})
        else:
            fake_entry = types.SimpleNamespace(raw={"priority": 1, "pp": 15})
        engine.MOVEDEX[key] = fake_entry

        participant = types.SimpleNamespace(name="AI Trainer")
        move_stub = types.SimpleNamespace(name=move_name.lower(), pp=None, current_pp=None)
        active_pokemon = types.SimpleNamespace(moves=[move_stub])
        opponent = types.SimpleNamespace(active=[object()])

        class StubBattle:
            def __init__(self, foe):
                self.rng = random.Random(0)
                self._foe = foe

            def opponents_of(self, part):
                return [self._foe]

        battle = StubBattle(opponent)

        action = engine._select_ai_action(participant, active_pokemon, battle)

        expected_pp = get_pp(fake_entry)
        assert expected_pp is not None
        assert action.move.pp == expected_pp
        assert action.move.priority == 1
    finally:
        if original_entry is None:
            engine.MOVEDEX.pop(key, None)
        else:
            engine.MOVEDEX[key] = original_entry
