import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Minimal pokemon.dex stub with a Pikachu entry
pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.POKEDEX = {"pikachu": object()}
sys.modules["pokemon.dex"] = pokemon_dex

# Stub pokemon.generation.generate_pokemon
class DummyInst:
    def __init__(self, level):
        self.species = types.SimpleNamespace(name="Pikachu", types=["Electric"])
        self.level = level
        self.gender = "M"
        self.nature = "Hardy"
        self.ability = "Static"
        self.ivs = types.SimpleNamespace(hp=1, atk=2, def_=3, spa=4, spd=5, spe=6)

gen_mod = types.ModuleType("pokemon.generation")

def generate_pokemon(name, level=5):
    return DummyInst(level)

gen_mod.generate_pokemon = generate_pokemon
sys.modules["pokemon.generation"] = gen_mod

# Stub OwnedPokemon model and heal_pokemon function
heal_calls = []

class FakePokemon:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.set_level_called = None

    def set_level(self, level):
        self.set_level_called = level
        self.level = level

class FakeManager:
    def __init__(self):
        self.created = None

    def create(self, **kwargs):
        self.created = kwargs
        mon = FakePokemon(**kwargs)
        return mon

FakePokemon.objects = FakeManager()

models_mod = types.ModuleType("pokemon.models")
models_mod.OwnedPokemon = FakePokemon
sys.modules["pokemon.models"] = models_mod

commands_mod = types.ModuleType("commands.command")

def heal_pokemon(pokemon):
    heal_calls.append(pokemon)

commands_mod.heal_pokemon = heal_pokemon
sys.modules["commands.command"] = commands_mod

# Load the menu module under test
path = os.path.join(ROOT, "menus", "give_pokemon.py")
spec = importlib.util.spec_from_file_location("menus.give_pokemon", path)
give_mod = importlib.util.module_from_spec(spec)
sys.modules["menus.give_pokemon"] = give_mod
spec.loader.exec_module(give_mod)


class DummyAttr(types.SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


class DummyStorage:
    def __init__(self):
        self.active_pokemon = types.SimpleNamespace(count=lambda: 0)
        self.added = None

    def add_active_pokemon(self, mon):
        self.added = mon


class DummyChar:
    def __init__(self, key):
        self.key = key
        self.ndb = DummyAttr()
        self.trainer = object()
        self.storage = DummyStorage()
        self.msgs = []

    def msg(self, text):
        self.msgs.append(text)


def test_node_start_sets_species():
    caller = DummyChar("Admin")
    target = DummyChar("Target")
    nxt, opts = give_mod.node_start(caller, "Pikachu", target=target)
    assert nxt == "node_level"
    assert caller.ndb.givepoke["species"] == "Pikachu"


def test_node_level_creates_pokemon():
    caller = DummyChar("Admin")
    target = DummyChar("Target")
    caller.ndb.givepoke = {"species": "Pikachu"}

    nxt, opts = give_mod.node_level(caller, "5", target=target)

    created = FakePokemon.objects.created
    assert created["trainer"] == target.trainer
    assert created["species"] == "Pikachu"
    assert created["nickname"] == ""
    assert created["gender"] == "M"
    assert created["nature"] == "Hardy"
    assert created["ability"] == "Static"
    assert created["ivs"] == [1, 2, 3, 4, 5, 6]
    assert created["evs"] == [0, 0, 0, 0, 0, 0]

    mon = target.storage.added
    assert mon is not None
    assert mon.set_level_called == 5
    assert heal_calls[-1] is mon
    assert caller.msgs
    assert target.msgs
    assert nxt is None and opts is None
    assert not hasattr(caller.ndb, "givepoke")

