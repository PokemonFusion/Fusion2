import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_module():
	path = os.path.join(ROOT, "pokemon", "battle", "battleinstance.py")
	iface = types.ModuleType("pokemon.battle.interface")
	iface.display_battle_interface = lambda *a, **k: None
	iface.format_turn_banner = lambda turn, *, closing=False: ""
	iface.render_interfaces = lambda *a, **k: ("", "", "")
	sys.modules["pokemon.battle.interface"] = iface
	watchers = types.ModuleType("pokemon.battle.watchers")
	watchers.add_watcher = lambda *a, **k: None
	watchers.notify_watchers = lambda *a, **k: None
	watchers.remove_watcher = lambda *a, **k: None
	watchers.WatcherManager = type(
		"WatcherManager",
		(),
		{
			"add_watcher": lambda self, watcher: None,
			"remove_watcher": lambda self, watcher: None,
			"notify": lambda self, msg: None,
			"add_observer": lambda self, watcher: None,
			"remove_observer": lambda self, watcher: None,
		},
	)
	sys.modules["pokemon.battle.watchers"] = watchers
	handler_mod = types.ModuleType("pokemon.battle.handler")
	handler_mod.battle_handler = types.SimpleNamespace(
		register=lambda *a, **k: None,
		unregister=lambda *a, **k: None,
		restore=lambda *a, **k: None,
		save=lambda *a, **k: None,
		next_id=lambda: 1,
	)
	sys.modules["pokemon.battle.handler"] = handler_mod
	spec = importlib.util.spec_from_file_location("pokemon.battle.battleinstance", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)
	return mod


def test_prepare_party_uses_active_moves():
	bi = load_module()
	bi._calc_stats_from_model = lambda poke: {"hp": 30}

	class FakeSlot:
		def __init__(self, name, slot):
			self.move = types.SimpleNamespace(name=name)
			self.slot = slot

	class FakeQS(list):
		def all(self):
			return self

		def order_by(self, field):
			return self

	class FakePoke:
		def __init__(self):
			self.name = "Pika"
			self.level = 5
			self.current_hp = 30
			self.activemoveslot_set = FakeQS([FakeSlot("tackle", 1), FakeSlot("growl", 2)])
			self.ability = None
			self.ivs = [0, 0, 0, 0, 0, 0]
			self.evs = [0, 0, 0, 0, 0, 0]
			self.nature = "Hardy"

	class FakeStorage:
		def get_party(self):
			return [FakePoke()]

	trainer = types.SimpleNamespace(key="Ash", storage=FakeStorage())
	session = object.__new__(bi.BattleSession)

	party = bi.BattleSession._prepare_player_party(session, trainer)
	assert [m.name for m in party[0].moves] == ["tackle", "growl"]
	assert hasattr(party[0], "activemoveslot_set")


def test_prepare_party_uses_moveset_when_no_slots():
	bi = load_module()
	bi._calc_stats_from_model = lambda poke: {"hp": 30}

	class FakeSlot:
		def __init__(self, name, slot):
			self.move = types.SimpleNamespace(name=name)
			self.slot = slot

	class FakeQS(list):
		def all(self):
			return self

		def order_by(self, field):
			return self

	class FakeMoveset:
		def __init__(self):
			self.slots = FakeQS([FakeSlot("tackle", 1), FakeSlot("growl", 2)])

	class FakePoke:
		def __init__(self):
			self.name = "Pika"
			self.level = 5
			self.current_hp = 30
			self.active_moveset = FakeMoveset()
			self.ability = None
			self.ivs = [0, 0, 0, 0, 0, 0]
			self.evs = [0, 0, 0, 0, 0, 0]
			self.nature = "Hardy"

	class FakeStorage:
		def get_party(self):
			return [FakePoke()]

	trainer = types.SimpleNamespace(key="Ash", storage=FakeStorage())
	session = object.__new__(bi.BattleSession)

	party = bi.BattleSession._prepare_player_party(session, trainer)
	assert [m.name for m in party[0].moves] == ["tackle", "growl"]
	assert hasattr(party[0], "activemoveslot_set")
