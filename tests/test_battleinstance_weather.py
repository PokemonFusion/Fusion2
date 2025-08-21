import importlib.util
import os
import sys
import types
from enum import Enum

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Stub evennia.create_object while keeping the real module
try:
	import evennia  # type: ignore

	orig_create_object = evennia.create_object
except Exception:  # Module doesn't exist in minimal test env
	evennia = types.ModuleType("evennia")

	def _create_object_stub(cls, key=None):
		return cls()

	orig_create_object = _create_object_stub
	evennia.create_object = _create_object_stub

	def _search_object_stub(*args, **kwargs):
		return []

	evennia.search_object = _search_object_stub
	evennia.DefaultRoom = type("DefaultRoom", (), {})
	evennia.objects = types.SimpleNamespace(objects=types.SimpleNamespace(DefaultRoom=evennia.DefaultRoom))
	evennia.utils = types.ModuleType("evennia.utils")

	def _identity(s):
		return s

	evennia.utils.ansi = types.SimpleNamespace(
		parse_ansi=_identity,
		RED=_identity,
		GREEN=_identity,
		YELLOW=_identity,
		BLUE=_identity,
		MAGENTA=_identity,
		CYAN=_identity,
		strip_ansi=_identity,
	)
	sys.modules["evennia.utils"] = evennia.utils
	evennia.server = types.ModuleType("evennia.server")
	evennia.server.models = types.ModuleType("evennia.server.models")
	evennia.server.models.ServerConfig = type("ServerConfig", (), {})
	sys.modules["evennia.server"] = evennia.server
	sys.modules["evennia.server.models"] = evennia.server.models
	sys.modules["evennia"] = evennia
else:

	def _create_object_stub(cls, key=None):
		return cls()

	evennia.create_object = _create_object_stub

# Stub BattleRoom
rooms_mod = types.ModuleType("typeclasses.rooms")


class BattleRoom:
	def __init__(self, key=None):
		self.key = key
		self.db = types.SimpleNamespace()
		self.ndb = types.SimpleNamespace()
		self.locks = types.SimpleNamespace(add=lambda *a, **k: None)

	def delete(self):
		pass


rooms_mod.BattleRoom = BattleRoom
rooms_mod.MapRoom = type("MapRoom", (), {})
rooms_mod.Room = type("Room", (), {})
sys.modules["typeclasses.rooms"] = rooms_mod

# Stub interface functions and watchers
iface = types.ModuleType("pokemon.battle.interface")


def _display_battle_interface(*args, **kwargs):
	return ""


def _format_turn_banner(turn):
	return ""


def _render_interfaces(*args, **kwargs):
	return ("", "", "")


iface.display_battle_interface = _display_battle_interface
iface.format_turn_banner = _format_turn_banner
iface.render_interfaces = _render_interfaces
sys.modules["pokemon.battle.interface"] = iface
watchers = types.ModuleType("pokemon.battle.watchers")


def _noop(*args, **kwargs):
	return None


watchers.add_watcher = _noop
watchers.remove_watcher = _noop
watchers.notify_watchers = _noop


class WatcherManager:
	def add_watcher(self, w):
		return None

	def remove_watcher(self, w):
		return None

	def notify(self, m):
		return None

	def add_observer(self, w):
		return None

	def remove_observer(self, w):
		return None


watchers.WatcherManager = WatcherManager
sys.modules["pokemon.battle.watchers"] = watchers

# Stub battle handler
handler_mod = types.ModuleType("pokemon.battle.handler")
handler_mod.battle_handler = types.SimpleNamespace(
	register=lambda *a, **k: None,
	unregister=lambda *a, **k: None,
	restore=lambda *a, **k: None,
	save=lambda *a, **k: None,
	next_id=lambda: 1,
)
sys.modules["pokemon.battle.handler"] = handler_mod

# Stub pokemon generation
gen_mod = types.ModuleType("pokemon.data.generation")


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
sys.modules["pokemon.data.generation"] = gen_mod

# Stub spawn helper
spawn_mod = types.ModuleType("pokemon.helpers.pokemon_spawn")


def _get_spawn_stub(loc):
	return None


spawn_mod.get_spawn = _get_spawn_stub
sys.modules["pokemon.helpers.pokemon_spawn"] = spawn_mod

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

# Load storage module for battleinstance
storage_path = os.path.join(ROOT, "pokemon", "battle", "storage.py")
storage_spec = importlib.util.spec_from_file_location("pokemon.battle.storage", storage_path)
storage_mod = importlib.util.module_from_spec(storage_spec)
sys.modules[storage_spec.name] = storage_mod
storage_spec.loader.exec_module(storage_mod)

# Create package placeholders and load pokemon_factory
pokemon_pkg = types.ModuleType("pokemon")
pokemon_pkg.__path__ = [os.path.join(ROOT, "pokemon")]
sys.modules["pokemon"] = pokemon_pkg
battle_pkg = types.ModuleType("pokemon.battle")
battle_pkg.__path__ = [os.path.join(ROOT, "pokemon", "battle")]
sys.modules["pokemon.battle"] = battle_pkg

pf_path = os.path.join(ROOT, "pokemon", "battle", "pokemon_factory.py")
pf_spec = importlib.util.spec_from_file_location("pokemon.battle.pokemon_factory", pf_path)
pf_mod = importlib.util.module_from_spec(pf_spec)
sys.modules[pf_spec.name] = pf_mod
pf_spec.loader.exec_module(pf_mod)

# Now load battleinstance
bi_path = os.path.join(ROOT, "pokemon", "battle", "battleinstance.py")
bi_spec = importlib.util.spec_from_file_location("pokemon.battle.battleinstance", bi_path)
bi_mod = importlib.util.module_from_spec(bi_spec)
sys.modules[bi_spec.name] = bi_mod
bi_spec.loader.exec_module(bi_mod)
BattleSession = bi_mod.BattleSession


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
	inst = BattleSession(player)
	inst.start()
	assert inst.state.roomweather == "rain"
	evennia.create_object = orig_create_object
