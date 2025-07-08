import os
import sys
import types
import importlib.util
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Store originals
import evennia
orig_create_object = evennia.create_object
orig_models = sys.modules.get("pokemon.models")
orig_generation = sys.modules.get("pokemon.generation")
orig_spawn = sys.modules.get("world.pokemon_spawn")
orig_capture = sys.modules.get("pokemon.battle.capture")

battleroom_mod = types.ModuleType("typeclasses.battleroom")
class BattleRoom:
    def __init__(self, key=None):
        self.key = key
        self.db = types.SimpleNamespace()
        self.locks = types.SimpleNamespace(add=lambda *a, **k: None)
    def delete(self):
        pass
battleroom_mod.BattleRoom = BattleRoom

# Interface and handler stubs
iface = types.ModuleType("pokemon.battle.interface")
iface.add_watcher = lambda *a, **k: None
iface.remove_watcher = lambda *a, **k: None
iface.notify_watchers = lambda *a, **k: None

handler_mod = types.ModuleType("pokemon.battle.handler")
handler_mod.battle_handler = types.SimpleNamespace(register=lambda *a, **k: None,
                                                   unregister=lambda *a, **k: None,
                                                   restore=lambda *a, **k: None,
                                                   save=lambda *a, **k: None)

# Pokemon model stub
class FakeCollection:
    def __init__(self):
        self.items = []
    def add(self, obj):
        self.items.append(obj)
    def all(self):
        return self.items

class FakeManager:
    def __init__(self):
        self.store = {}
        self.counter = 1
    def create(self, **kwargs):
        obj = FakePokemon(**kwargs)
        obj.id = self.counter
        self.counter += 1
        self.store[obj.id] = obj
        return obj
    def get(self, id):
        return self.store[id]

class FakePokemon:
    objects = FakeManager()
    def __init__(self, name, level, type_, trainer=None, ability=None, data=None, temporary=False):
        self.name = name
        self.level = level
        self.type_ = type_
        self.trainer = trainer
        self.temporary = temporary
        self.data = data or {}
    def save(self):
        pass
    def delete(self):
        self.__class__.objects.store.pop(self.id, None)

models_mod = types.ModuleType("pokemon.models")
models_mod.Pokemon = FakePokemon

# Generation and stats stubs
class DummyInst:
    def __init__(self, name, level):
        self.species = types.SimpleNamespace(name=name, types=["Electric"])
        self.level = level
        self.stats = types.SimpleNamespace(hp=10)
        self.moves = ["tackle"]
        self.ability = None

gen_mod = types.ModuleType("pokemon.generation")

def generate_pokemon(name, level=5):
    return DummyInst(name, level)

gen_mod.generate_pokemon = generate_pokemon
gen_mod.NATURES = {}

spawn_mod = types.ModuleType("world.pokemon_spawn")
spawn_mod.get_spawn = lambda loc: None

# ------------------------------------------------------------
# Test setup/teardown
# ------------------------------------------------------------

def setup_module(module):
    evennia.create_object = lambda cls, key=None: cls()
    sys.modules["typeclasses.battleroom"] = battleroom_mod
    sys.modules["pokemon.battle.interface"] = iface
    sys.modules["pokemon.battle.handler"] = handler_mod
    sys.modules["pokemon.models"] = models_mod
    sys.modules["pokemon.generation"] = gen_mod
    sys.modules["world.pokemon_spawn"] = spawn_mod

    cap_path = os.path.join(ROOT, "pokemon", "battle", "capture.py")
    cap_spec = importlib.util.spec_from_file_location("pokemon.battle.capture", cap_path)
    cap_mod = importlib.util.module_from_spec(cap_spec)
    sys.modules[cap_spec.name] = cap_mod
    cap_spec.loader.exec_module(cap_mod)
    cap_mod.attempt_capture = lambda *a, **k: True
    sys.modules["pokemon.battle.capture"] = cap_mod

    bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
    bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
    module.bd_mod = importlib.util.module_from_spec(bd_spec)
    sys.modules[bd_spec.name] = module.bd_mod
    bd_spec.loader.exec_module(module.bd_mod)
    module.Pokemon = module.bd_mod.Pokemon

    st_path = os.path.join(ROOT, "pokemon", "battle", "state.py")
    st_spec = importlib.util.spec_from_file_location("pokemon.battle.state", st_path)
    module.st_mod = importlib.util.module_from_spec(st_spec)
    sys.modules[st_spec.name] = module.st_mod
    st_spec.loader.exec_module(module.st_mod)

    eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
    eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
    module.engine = importlib.util.module_from_spec(eng_spec)
    sys.modules[eng_spec.name] = module.engine
    eng_spec.loader.exec_module(module.engine)
    module.Battle = module.engine.Battle
    module.BattleParticipant = module.engine.BattleParticipant
    module.Action = module.engine.Action
    module.ActionType = module.engine.ActionType
    module.BattleType = module.engine.BattleType

    bi_path = os.path.join(ROOT, "pokemon", "battle", "battleinstance.py")
    bi_spec = importlib.util.spec_from_file_location("pokemon.battle.battleinstance", bi_path)
    module.bi_mod = importlib.util.module_from_spec(bi_spec)
    sys.modules[bi_spec.name] = module.bi_mod
    bi_spec.loader.exec_module(module.bi_mod)
    module.BattleInstance = module.bi_mod.BattleInstance

# Dummy classes
class DummyStorage:
    def __init__(self):
        self.active_pokemon = types.SimpleNamespace(all=lambda: [])
        self.stored_pokemon = FakeCollection()

class DummyRoom:
    def __init__(self):
        self.db = types.SimpleNamespace(weather="clear")

class DummyAttr(types.SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)

class DummyPlayer:
    def __init__(self):
        self.key = "Player"
        self.id = 1
        self.db = types.SimpleNamespace()
        self.ndb = DummyAttr()
        self.location = DummyRoom()
        self.storage = DummyStorage()
        self.trainer = "trainer"
    def msg(self, *a, **k):
        pass
    def move_to(self, room, quiet=False):
        self.location = room

def test_temp_pokemon_persists_after_restore():
    random_choice = bi_mod.random.choice
    bi_mod.random.choice = lambda opts: "pokemon"
    player = DummyPlayer()
    inst = BattleInstance(player)
    inst.start()
    pid = inst.temp_pokemon_ids[0]
    assert pid in FakePokemon.objects.store
    restored = BattleInstance.restore(inst.room)
    assert pid in restored.temp_pokemon_ids
    bi_mod.random.choice = random_choice


def test_capture_converts_pokemon():
    wild_db = FakePokemon.objects.create(name="Bulbasaur", level=5, type_="Grass", temporary=True)
    wild = Pokemon("Bulbasaur", hp=1, max_hp=10, model_id=wild_db.id)
    attacker = Pokemon("Pikachu")
    p1 = BattleParticipant("P1", [attacker], is_ai=False)
    p2 = BattleParticipant("P2", [wild], is_ai=False)
    p1.active = [attacker]
    p2.active = [wild]
    p1.trainer = "trainer"
    p1.storage = types.SimpleNamespace(stored_pokemon=FakeCollection())
    action = Action(p1, ActionType.ITEM, p2, item="Pokeball", priority=6)
    p1.pending_action = action
    random.seed(0)
    battle = Battle(BattleType.WILD, [p1, p2])
    battle.run_turn()
    dbpoke = FakePokemon.objects.get(wild_db.id)
    assert dbpoke.trainer == "trainer"
    assert dbpoke.temporary is False
    assert dbpoke in p1.storage.stored_pokemon.items


def test_uncaught_pokemon_deleted_on_end():
    random_choice = bi_mod.random.choice
    bi_mod.random.choice = lambda opts: "pokemon"
    player = DummyPlayer()
    inst = BattleInstance(player)
    inst.start()
    pid = inst.temp_pokemon_ids[0]
    inst.end()
    assert pid not in FakePokemon.objects.store
    bi_mod.random.choice = random_choice

def teardown_module(module):
    evennia.create_object = orig_create_object
    if orig_models is not None:
        sys.modules["pokemon.models"] = orig_models
    else:
        sys.modules.pop("pokemon.models", None)
    if orig_generation is not None:
        sys.modules["pokemon.generation"] = orig_generation
    else:
        sys.modules.pop("pokemon.generation", None)
    if orig_spawn is not None:
        sys.modules["world.pokemon_spawn"] = orig_spawn
    else:
        sys.modules.pop("world.pokemon_spawn", None)
    if orig_capture is not None:
        sys.modules["pokemon.battle.capture"] = orig_capture
    else:
        sys.modules.pop("pokemon.battle.capture", None)
