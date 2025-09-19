import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Provide a minimal evennia stub if the real module isn't available
if "evennia" not in sys.modules:
	evennia = types.ModuleType("evennia")
	evennia.DefaultRoom = type("DefaultRoom", (), {})
	evennia.objects = types.SimpleNamespace(objects=types.SimpleNamespace(DefaultRoom=evennia.DefaultRoom))
	evennia.create_object = lambda *a, **k: None
	evennia.search_object = lambda *a, **k: []
	sys.modules["evennia"] = evennia

# Provide a lightweight battle system stub so ``world.hunt_system`` can import
# its dependencies without requiring the real game engine.
orig_pokemon_pkg = sys.modules.get("pokemon")
if orig_pokemon_pkg is None:
	import pokemon as orig_pokemon_pkg  # type: ignore
if "pokemon.battle.battleinstance" not in sys.modules:
	battle_mod = types.ModuleType("pokemon.battle.battleinstance")

	class BattleType:
		WILD = "wild"
		TRAINER = "trainer"

	class BattleSession:
		def __init__(self, player, opponent=None):
			self.captainA = player

		def start(self):
			pass

	def create_battle_pokemon(name, level, is_wild=False):
		return types.SimpleNamespace(name=name, level=level)

	def generate_trainer_pokemon():
		return types.SimpleNamespace(name="Rattata", level=5)

	battle_mod.BattleType = BattleType
	battle_mod.BattleSession = BattleSession
	battle_mod.create_battle_pokemon = create_battle_pokemon
	battle_mod.generate_trainer_pokemon = generate_trainer_pokemon

	# Ensure the parent packages exist in ``sys.modules``
	if "pokemon.battle" not in sys.modules:
		sys.modules["pokemon.battle"] = types.ModuleType("pokemon.battle")
	sys.modules["pokemon.battle.battleinstance"] = battle_mod

from world.hunt_system import HuntSystem


class DummyDB(types.SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)


class DummyRoom:
	def __init__(self):
		# use a 0 encounter rate to ensure fixed hunts ignore it
		self.db = DummyDB(allow_hunting=True, encounter_rate=0)
		self.ndb = DummyDB()


class DummyAttr(types.SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)


class DummyStorage:
	def get_party(self):
		return [types.SimpleNamespace(ability=None, current_hp=10)]


class DummyHunter:
	def __init__(self):
		self.key = "hunter"
		self.db = DummyAttr(training_points=10)
		self.ndb = DummyAttr()
		self.storage = DummyStorage()
		self.location = DummyRoom()


def test_perform_fixed_hunt():
	room = DummyRoom()
	captured = {}

	def cb(hunter, data):
		captured.update(data)

	hs = HuntSystem(room, spawn_callback=cb)
	hunter = DummyHunter()
	hunter.location = room
	msg = hs.perform_fixed_hunt(hunter, "Pikachu", 7)
	assert msg == "A wild Pikachu (Lv 7) appeared!"
	assert captured["name"] == "Pikachu"
	assert captured["level"] == 7


def teardown_module(module):
	if orig_pokemon_pkg is not None:
		sys.modules["pokemon"] = orig_pokemon_pkg
	else:
		sys.modules.pop("pokemon", None)


def test_allow_hunting_string_value():
	room = DummyRoom()
	room.db.allow_hunting = "true"
	hs = HuntSystem(room)
	hunter = DummyHunter()
	hunter.location = room
	msg = hs.perform_fixed_hunt(hunter, "Pidgey", 5)
	assert msg.startswith("A wild Pidgey")


def test_hunt_not_allowed():
	room = DummyRoom()
	room.db.allow_hunting = False
	hs = HuntSystem(room)
	hunter = DummyHunter()
	msg = hs.perform_fixed_hunt(hunter, "Rattata", 3)
	assert msg == "You can't hunt here."


def test_hunt_requires_conscious_pokemon():
	room = DummyRoom()
	hs = HuntSystem(room)
	hunter = DummyHunter()
	hunter.location = room

	class FaintedStorage(DummyStorage):
		def get_party(self):
			return [types.SimpleNamespace(ability=None, current_hp=0)]

	hunter.storage = FaintedStorage()
	msg = hs.perform_hunt(hunter)
	assert msg == "You don't have any Pokémon able to battle."
