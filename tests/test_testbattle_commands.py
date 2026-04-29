import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

orig_evennia = sys.modules.get("evennia")
orig_battleinstance = sys.modules.get("pokemon.battle.battleinstance")
orig_dex = sys.modules.get("pokemon.dex")

fake_evennia = types.ModuleType("evennia")
fake_evennia.Command = type("Command", (), {"parse": lambda self: None})
sys.modules["evennia"] = fake_evennia

session_calls = []
fake_battleinstance = types.ModuleType("pokemon.battle.battleinstance")


class FakeBattleSession:
	def __init__(self, player):
		self.player = player
		self.battle_id = 77

	def start_test_battle(self, **kwargs):
		session_calls.append({"player": self.player, **kwargs})


fake_battleinstance.BattleSession = FakeBattleSession
sys.modules["pokemon.battle.battleinstance"] = fake_battleinstance

path = os.path.join(ROOT, "commands", "admin", "cmd_testbattle.py")
spec = importlib.util.spec_from_file_location("commands.admin.cmd_testbattle", path)
cmd_mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cmd_mod
spec.loader.exec_module(cmd_mod)


class DummyRoom:
	def __init__(self):
		self.db = types.SimpleNamespace()


class DummyTarget:
	def __init__(self, key="Target"):
		self.key = key
		self.location = DummyRoom()
		self.ndb = types.SimpleNamespace()


class DummyCaller(DummyTarget):
	def __init__(self):
		super().__init__("Caller")
		self.messages = []
		self.search_result = None

	def msg(self, text):
		self.messages.append(text)

	def search(self, *args, **kwargs):
		return self.search_result


def test_testspawn_sets_room_payload():
	cmd = cmd_mod.CmdTestSpawn()
	caller = DummyCaller()
	cmd.caller = caller
	cmd.args = "Pikachu, 12, trainer"
	cmd.switches = []

	cmd.parse()
	cmd.func()

	assert caller.location.db.test_battle_spawn == {
		"species": "Pikachu",
		"level": 12,
		"kind": "trainer",
	}


def test_testspawn_unknown_species_reports_suggestion():
	fake_dex = types.ModuleType("pokemon.dex")
	fake_dex.POKEDEX = {
		"squirtle": types.SimpleNamespace(name="Squirtle"),
		"wartortle": types.SimpleNamespace(name="Wartortle"),
	}
	sys.modules["pokemon.dex"] = fake_dex
	cmd = cmd_mod.CmdTestSpawn()
	caller = DummyCaller()
	cmd.caller = caller
	cmd.args = "Squirtel, 12, trainer"
	cmd.switches = []

	try:
		cmd.parse()
		cmd.func()
	finally:
		if orig_dex is not None:
			sys.modules["pokemon.dex"] = orig_dex
		else:
			sys.modules.pop("pokemon.dex", None)

	assert not hasattr(caller.location.db, "test_battle_spawn")
	assert "Species 'Squirtel' was not found in the Pokedex." in caller.messages[-1]
	assert "Did you mean Squirtle?" in caller.messages[-1]


def test_starttestbattle_uses_room_payload():
	session_calls.clear()
	cmd = cmd_mod.CmdStartTestBattle()
	caller = DummyCaller()
	target = DummyTarget("Red")
	target.location = caller.location
	caller.search_result = target
	caller.location.db.test_battle_spawn = {
		"species": "Bulbasaur",
		"level": 9,
		"kind": "wild",
	}
	cmd.caller = caller
	cmd.args = "Red"

	cmd.func()

	assert session_calls
	call = session_calls[-1]
	assert call["player"] is target
	assert call["species"] == "Bulbasaur"
	assert call["level"] == 9
	assert call["opponent_kind"] == "wild"


def teardown_module():
	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)
	if orig_battleinstance is not None:
		sys.modules["pokemon.battle.battleinstance"] = orig_battleinstance
	else:
		sys.modules.pop("pokemon.battle.battleinstance", None)
	if orig_dex is not None:
		sys.modules["pokemon.dex"] = orig_dex
	else:
		sys.modules.pop("pokemon.dex", None)
