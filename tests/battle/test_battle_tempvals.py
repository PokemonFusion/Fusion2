from __future__ import annotations

import random
from collections.abc import MutableMapping
from types import SimpleNamespace

from pokemon.battle.battledata import Pokemon, TurnInit
from pokemon.battle.engine import Battle, BattleParticipant, BattleType
from pokemon.battle.turnorder import _Priority


class AutosavingMapping(MutableMapping):
    """Mapping that fails if battle code mutates it in place."""

    def __init__(self, values=None):
        self.data = dict(values or {})

    def __getitem__(self, key):
        return self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __setitem__(self, key, value):
        raise AssertionError("autosaving mapping was mutated")

    def __delitem__(self, key):
        raise AssertionError("autosaving mapping was mutated")


def test_run_after_switch_replaces_persistent_tempvals_mapping():
    user = Pokemon("Bulbasaur")
    target = Pokemon("Pidgey")
    user.tempvals = AutosavingMapping({"moved": True})

    p1 = BattleParticipant("P1", [user], is_ai=False)
    p2 = BattleParticipant("P2", [target])
    p1.active = [user]
    p2.active = [target]

    battle = Battle(BattleType.WILD, [p1, p2])
    battle.run_after_switch()

    assert user.tempvals == {}
    assert isinstance(user.tempvals, dict)


def test_turnorder_replaces_persistent_tempvals_mapping():
    pokemon = SimpleNamespace(tempvals=AutosavingMapping({"moved": True}), speed=1)

    _Priority(TurnInit(), pokemon, random.Random(1))

    assert pokemon.tempvals == {}
    assert isinstance(pokemon.tempvals, dict)


def test_pokemon_from_dict_detaches_persistent_tempvals_mapping():
    stored_tempvals = AutosavingMapping({"moved": True})
    stored_boosts = AutosavingMapping({"atk": 1})

    pokemon = Pokemon.from_dict(
        {
            "name": "Bulbasaur",
            "tempvals": stored_tempvals,
            "boosts": stored_boosts,
        }
    )
    pokemon.tempvals["new_turn_flag"] = True
    pokemon.boosts["def"] = 1

    assert pokemon.tempvals == {"moved": True, "new_turn_flag": True}
    assert pokemon.boosts == {"atk": 1, "def": 1}
    assert stored_tempvals.data == {"moved": True}
    assert stored_boosts.data == {"atk": 1}
