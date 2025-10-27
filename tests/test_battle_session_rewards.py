import math
import sys
import types

import pytest

# Ensure real battle modules are used even if other tests stubbed them.
for name in [key for key in list(sys.modules) if key.startswith("pokemon.battle")]:
    sys.modules.pop(name)

from pokemon.battle.battledata import Pokemon
from pokemon.battle.battleinstance import BattleSession
from pokemon.battle.engine import BattleType
from pokemon.dex.exp_ev_yields import GAIN_INFO
import pokemon.models.stats as stats_mod


class StubPartyManager:
    def __init__(self, mons):
        self._mons = mons

    def all(self):
        return list(self._mons)


class StubStorage:
    def __init__(self, mons):
        self._mons = mons
        self.active_pokemon = StubPartyManager(mons)

    def get_party(self):
        return list(self._mons)


class StubOwnedPokemon:
    def __init__(self, unique_id: str = "owned-1", species: str = "Eevee", level: int = 5):
        self.unique_id = unique_id
        self.species = species
        self.name = species
        self.level = level
        self.total_exp = level ** 3  # align with medium_fast curve
        self.current_hp = 30
        self.max_hp = 30
        self.evs: dict[str, int] = {}
        self.growth_rate = "medium_fast"
        self.moves = ["Tackle"]
        self.saved = False

    def save(self):
        self.saved = True


class StubLocation:
    def __init__(self):
        self.id = 7
        self.db = types.SimpleNamespace(battles=[])
        self.ndb = types.SimpleNamespace(battle_instances={})


class StubPlayer:
    def __init__(self, mons):
        self.id = 42
        self.key = "Player"
        self.storage = StubStorage(mons)
        self.db = types.SimpleNamespace(exp_share=False)
        self.ndb = types.SimpleNamespace()
        self.location = StubLocation()
        self.messages: list[str] = []

    def msg(self, text):
        self.messages.append(text)


@pytest.mark.parametrize("species", ["Pikachu"])
def test_battle_session_grants_rewards(monkeypatch, species):
    monkeypatch.setattr(stats_mod, "learn_level_up_moves", lambda pokemon, caller=None, prompt=True: None)

    owned = StubOwnedPokemon(unique_id="stub-1", species="Eevee", level=5)
    player = StubPlayer([owned])

    player_mon = Pokemon(owned.species, level=owned.level, hp=owned.current_hp, max_hp=owned.max_hp)
    player_mon.model_id = owned.unique_id

    wild_gain = GAIN_INFO[species]
    wild = Pokemon(species, level=5, hp=0, max_hp=20)

    temp_id = 9999

    class RewardSession(BattleSession):
        def _select_opponent(self):
            wild.model_id = temp_id
            self.temp_pokemon_ids.append(temp_id)
            return wild, "Wild", BattleType.WILD, None

        def _prepare_player_party(self, trainer, full_heal: bool = False):
            return [player_mon]

    session = RewardSession(player)

    try:
        session.start()
        battle = session.battle
        assert battle is not None

        # Ensure the player's participant is active so rewards can be distributed.
        for participant in battle.participants:
            if participant.player is player:
                participant.active = [player_mon]
            else:
                participant.active = [wild]

        initial_exp = owned.total_exp
        battle.run_faint()

        expected_gain = math.floor(wild_gain["exp"] * wild.level / 7)
        assert owned.total_exp == initial_exp + expected_gain
        assert owned.evs.get("speed") == wild_gain["evs"].get("spe", 0)
        assert owned.saved is True
    finally:
        if temp_id in session.temp_pokemon_ids:
            session.temp_pokemon_ids.remove(temp_id)
        assert temp_id not in session.temp_pokemon_ids
