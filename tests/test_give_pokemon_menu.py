import types
import importlib.util
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# stub modules required by menu
orig_pokedex = sys.modules.get("pokemon.dex")
fake_pokedex = types.ModuleType("pokemon.dex")
fake_pokedex.POKEDEX = {"Pikachu": {}}
sys.modules["pokemon.dex"] = fake_pokedex

fake_generation = types.ModuleType("pokemon.generation")
class DummyInstance:
    def __init__(self, species, level):
        self.species = types.SimpleNamespace(name=species)
        self.level = level
        self.gender = "M"
        self.nature = "Hardy"
        self.ability = "Static"
        self.ivs = types.SimpleNamespace(hp=1, atk=1, def_=1, spa=1, spd=1, spe=1)

def generate_pokemon(species, level=1):
    return DummyInstance(species, level)
fake_generation.generate_pokemon = generate_pokemon
sys.modules["pokemon.generation"] = fake_generation

fake_models = types.ModuleType("pokemon.models")
class DummyObjects:
    def create(self, **kwargs):
        obj = OwnedPokemon()
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj

class OwnedPokemon:
    objects = DummyObjects()
    def set_level(self, lvl):
        self.level = lvl
    @property
    def computed_level(self):
        return self.level
    current_hp = 10
    def learn_level_up_moves(self):
        pass
    def heal(self):
        pass
fake_models.OwnedPokemon = OwnedPokemon
sys.modules["pokemon.models"] = fake_models

# load menu module with stubs in place
path = os.path.join(ROOT, "menus", "give_pokemon.py")
spec = importlib.util.spec_from_file_location("menus.give_pokemon", path)
menu = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = menu
spec.loader.exec_module(menu)

class DummyTarget:
    def __init__(self, count=0):
        self.key = "Target"
        self.trainer = types.SimpleNamespace()
        self.storage = types.SimpleNamespace(
            active_pokemon=types.SimpleNamespace(count=lambda: count),
            add_active_pokemon=lambda p: None,
        )
        self.msgs = []

    def msg(self, text):
        self.msgs.append(text)

class DummyCaller:
    def __init__(self):
        self.key = "Caller"
        self.ndb = types.SimpleNamespace()
        self.msgs = []

    def msg(self, text):
        self.msgs.append(text)


def test_target_preserved_across_nodes():
    caller = DummyCaller()
    target = DummyTarget()
    text, opts = menu.node_start(caller, target=target)
    option = opts[0]
    goto = option.get("goto")
    assert option.get("desc")
    assert isinstance(goto, tuple) and goto[1].get("target") is target
    text2, opts2 = menu.node_start(caller, raw_input="Pikachu", target=target)
    assert caller.ndb.givepoke["species"] == "Pikachu"
    option = opts2[0]
    goto = option.get("goto")
    assert isinstance(goto, tuple) and goto[1].get("target") is target

    text, opts = menu.node_level(caller, target=target)
    option = opts[0]
    goto = option.get("goto")
    assert option.get("desc")
    assert isinstance(goto, tuple) and goto[1].get("target") is target

    next_text, next_opts = menu.node_level(caller, raw_input="5", target=target)
    assert next_text is None and next_opts is None


def test_invalid_level_keeps_target():
    caller = DummyCaller()
    target = DummyTarget()
    caller.ndb.givepoke = {"species": "Pikachu"}
    text, opts = menu.node_level(caller, raw_input="foo", target=target)
    option = opts[0]
    assert option.get("goto")[1].get("target") is target


def teardown_module():
    if orig_pokedex is not None:
        sys.modules["pokemon.dex"] = orig_pokedex
    else:
        sys.modules.pop("pokemon.dex", None)
