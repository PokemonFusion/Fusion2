import os
import sys
import types
import importlib.util
from enum import Enum

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Stub evennia.create_object while keeping the real module
try:
    import evennia  # type: ignore
    orig_create_object = evennia.create_object
except Exception:  # Module doesn't exist in minimal test env
    evennia = types.ModuleType("evennia")
    orig_create_object = lambda cls, key=None: cls()
    evennia.create_object = orig_create_object
    evennia.search_object = lambda *a, **k: []
    evennia.DefaultRoom = type("DefaultRoom", (), {})
    evennia.objects = types.SimpleNamespace(objects=types.SimpleNamespace(DefaultRoom=evennia.DefaultRoom))
    evennia.utils = types.ModuleType("evennia.utils")
    evennia.utils.ansi = types.SimpleNamespace(
        parse_ansi=lambda s: s,
        RED=lambda s: s,
        GREEN=lambda s: s,
        YELLOW=lambda s: s,
        BLUE=lambda s: s,
        MAGENTA=lambda s: s,
        CYAN=lambda s: s,
        strip_ansi=lambda s: s,
    )
    sys.modules["evennia.utils"] = evennia.utils
    evennia.server = types.ModuleType("evennia.server")
    evennia.server.models = types.ModuleType("evennia.server.models")
    evennia.server.models.ServerConfig = type("ServerConfig", (), {})
    sys.modules["evennia.server"] = evennia.server
    sys.modules["evennia.server.models"] = evennia.server.models
    sys.modules["evennia"] = evennia
else:
    evennia.create_object = lambda cls, key=None: cls()

# Stub BattleRoom
battleroom_mod = types.ModuleType("typeclasses.battleroom")
class BattleRoom:
    def __init__(self, key=None):
        self.key = key
        self.db = types.SimpleNamespace()
        self.ndb = types.SimpleNamespace()
        self.locks = types.SimpleNamespace(add=lambda *a, **k: None)
    def delete(self):
        pass
battleroom_mod.BattleRoom = BattleRoom
sys.modules["typeclasses.battleroom"] = battleroom_mod

# Stub interface functions
iface = types.ModuleType("pokemon.battle.interface")
iface.add_watcher = lambda *a, **k: None
iface.remove_watcher = lambda *a, **k: None
iface.notify_watchers = lambda *a, **k: None
sys.modules["pokemon.battle.interface"] = iface

# Stub battle handler
handler_mod = types.ModuleType("pokemon.battle.handler")
handler_mod.battle_handler = types.SimpleNamespace(register=lambda *a, **k: None,
                                                   unregister=lambda *a, **k: None,
                                                   restore=lambda *a, **k: None,
                                                   save=lambda *a, **k: None)
sys.modules["pokemon.battle.handler"] = handler_mod

# Stub pokemon generation
gen_mod = types.ModuleType("pokemon.generation")
class DummyInst:
    def __init__(self, name, level):
        self.species = types.SimpleNamespace(name=name)
        self.level = level
        self.stats = types.SimpleNamespace(hp=100)
        self.moves = ["tackle"]
        self.ability = None

def generate_pokemon(name, level=5):
    return DummyInst(name, level)

gen_mod.generate_pokemon = generate_pokemon
sys.modules["pokemon.generation"] = gen_mod

# Stub spawn helper
spawn_mod = types.ModuleType("world.pokemon_spawn")
spawn_mod.get_spawn = lambda loc: None
sys.modules["world.pokemon_spawn"] = spawn_mod

# Minimal battle.engine stubs
engine_mod = types.ModuleType("pokemon.battle.engine")
class BattleType(Enum):
    WILD = 0
    PVP = 1
    TRAINER = 2
    SCRIPTED = 3
class BattleParticipant:
    def __init__(self, name, pokemons, is_ai=False):
        self.name = name
        self.pokemons = pokemons
        self.active = []
        self.is_ai = is_ai
        self.side = types.SimpleNamespace()
class Battle:
    def __init__(self, battle_type, parts):
        self.type = battle_type
        self.participants = parts
    def run_turn(self):
        pass
engine_mod.BattleType = BattleType
engine_mod.BattleParticipant = BattleParticipant
engine_mod.Battle = Battle
sys.modules["pokemon.battle.engine"] = engine_mod

# Load battledata and state modules from real files
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)

st_path = os.path.join(ROOT, "pokemon", "battle", "state.py")
st_spec = importlib.util.spec_from_file_location("pokemon.battle.state", st_path)
st_mod = importlib.util.module_from_spec(st_spec)
sys.modules[st_spec.name] = st_mod
st_spec.loader.exec_module(st_mod)

# Now load battleinstance
bi_path = os.path.join(ROOT, "pokemon", "battle", "battleinstance.py")
bi_spec = importlib.util.spec_from_file_location("pokemon.battle.battleinstance", bi_path)
bi_mod = importlib.util.module_from_spec(bi_spec)
sys.modules[bi_spec.name] = bi_mod
bi_spec.loader.exec_module(bi_mod)
BattleInstance = bi_mod.BattleInstance

# Dummy player
class DummyPoke:
    def __init__(self):
        self.name = "Pikachu"
        self.level = 5

class DummyStorage:
    def __init__(self):
        self.active_pokemon = types.SimpleNamespace(all=lambda: [DummyPoke()])

class DummyRoom:
    def __init__(self, weather="clear"):
        self.db = types.SimpleNamespace(weather=weather)
        self.ndb = types.SimpleNamespace()

class DummyPlayer:
    def __init__(self):
        self.key = "Player"
        self.id = 1
        self.db = types.SimpleNamespace()
        self.ndb = types.SimpleNamespace()
        self.location = DummyRoom(weather="rain")
        self.storage = DummyStorage()
    def msg(self, text):
        pass
    def move_to(self, room, quiet=False):
        self.location = room


def test_battle_state_uses_room_weather():
    player = DummyPlayer()
    inst = BattleInstance(player)
    inst.start()
    assert inst.state.roomweather == "rain"
    evennia.create_object = orig_create_object
