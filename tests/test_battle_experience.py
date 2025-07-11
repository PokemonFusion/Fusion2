import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Minimal pokemon.battle package
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
sys.modules["pokemon.battle"] = pkg_battle

# Load entity dataclasses
ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)

# Minimal pokemon.dex package
pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.entities = ent_mod
pokemon_dex.MOVEDEX = {}
pokemon_dex.POKEDEX = {}
sys.modules["pokemon.dex"] = pokemon_dex

# Load exp/ev yield data
yields_path = os.path.join(ROOT, "pokemon", "dex", "exp_ev_yields.py")
y_spec = importlib.util.spec_from_file_location("pokemon.dex.exp_ev_yields", yields_path)
y_mod = importlib.util.module_from_spec(y_spec)
sys.modules[y_spec.name] = y_mod
y_spec.loader.exec_module(y_mod)
GAIN_INFO = y_mod.GAIN_INFO

# Load stats module after stubbing dex
import pokemon.stats as stats_mod

# Load battledata and engine
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)
Pokemon = bd_mod.Pokemon

eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
eng_mod = importlib.util.module_from_spec(eng_spec)
sys.modules[eng_spec.name] = eng_mod
eng_spec.loader.exec_module(eng_mod)
Battle = eng_mod.Battle
BattleParticipant = eng_mod.BattleParticipant
BattleType = eng_mod.BattleType


class DummyMon:
    def __init__(self):
        self.experience = 0
        self.level = 1
        self.data = {"growth_rate": "medium_fast"}
        self.evs = {}
    def save(self):
        pass


class DummyManager:
    def __init__(self, mons):
        self._mons = mons
    def all(self):
        return list(self._mons)


class DummyStorage:
    def __init__(self, mons):
        self.active_pokemon = DummyManager(mons)


class DummyPlayer:
    def __init__(self, mons):
        self.db = types.SimpleNamespace(exp_share=False)
        self.storage = DummyStorage(mons)


def test_award_experience_on_faint():
    player_mon = DummyMon()
    player = DummyPlayer([player_mon])

    user = Pokemon("Bulbasaur", level=5, hp=50, max_hp=50)
    target = Pokemon("Pikachu", level=5, hp=0, max_hp=50)

    p1 = BattleParticipant("Player", [user], player=player)
    p2 = BattleParticipant("Wild", [target], is_ai=True)
    p1.active = [user]
    p2.active = [target]

    battle = Battle(BattleType.WILD, [p1, p2])
    battle.run_faint()

    gain = GAIN_INFO["Pikachu"]
    assert player_mon.experience == gain["exp"]
    assert player_mon.evs.get("spe") == gain["evs"]["spe"]

