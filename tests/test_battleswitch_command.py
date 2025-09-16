import importlib.util
import os
import sys
import types
from dataclasses import dataclass
from enum import Enum

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
	path = os.path.join(ROOT, "commands", "player", "cmd_battle_switch.py")
	spec = importlib.util.spec_from_file_location("commands.player.cmd_battle_switch", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)
	return mod


def setup_modules():
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")
	fake_evennia.Command = type("Command", (), {})
	utils_mod = types.ModuleType("evennia.utils")
	evmenu_mod = types.ModuleType("evennia.utils.evmenu")

	def fake_get_input(caller, prompt, callback, session=None, *a, **kw):
		caller.msg(prompt)
		caller.ndb.last_prompt_callback = callback

	evmenu_mod.get_input = fake_get_input
	utils_mod.evmenu = evmenu_mod

	fake_evennia.utils = utils_mod
	sys.modules["evennia"] = fake_evennia
	sys.modules["evennia.utils"] = utils_mod
	sys.modules["evennia.utils.evmenu"] = evmenu_mod

	orig_battle = sys.modules.get("pokemon.battle")
	battle_mod = types.ModuleType("pokemon.battle")

	class ActionType(Enum):
		MOVE = 1
		SWITCH = 2

	@dataclass
	class Action:
		actor: object
		action_type: ActionType
		target: object = None
		move: object = None
		priority: int = 0

	battle_mod.Action = Action
	battle_mod.ActionType = ActionType
	battle_mod.BattleMove = type("BattleMove", (), {})
	sys.modules["pokemon.battle"] = battle_mod

	return orig_evennia, orig_battle


def restore_modules(orig_evennia, orig_battle):
	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)
		try:
			import importlib

			real_evennia = importlib.import_module("evennia")
			sys.modules["evennia"] = real_evennia
		except Exception:
			evennia = types.ModuleType("evennia")
			evennia.search_object = lambda *a, **k: []
			evennia.create_object = lambda *a, **k: None
			sys.modules["evennia"] = evennia
	sys.modules.pop("evennia.utils.evmenu", None)
	sys.modules.pop("evennia.utils", None)
	if orig_battle is not None:
		sys.modules["pokemon.battle"] = orig_battle
	else:
		sys.modules.pop("pokemon.battle", None)


class FakeParticipant:
	def __init__(self, name, pokemons):
		self.name = name
		self.pokemons = pokemons
		self.active = [pokemons[0]]
		self.pending_action = None


class FakeBattle:
	def __init__(self, participants):
		self.participants = participants
		self.ran = False

	def opponent_of(self, part):
		for p in self.participants:
			if p is not part:
				return p
		return None

	def run_turn(self):
		self.ran = True


class FakeInstance:
	def __init__(self, battle):
		self.battle = battle
		self.ran = False

	def run_turn(self):
		self.ran = True
		self.battle.run_turn()

	def maybe_run_turn(self, actor=None):
		pass


class FakeQueueInstance(FakeInstance):
	def __init__(self, battle):
		super().__init__(battle)
		self.queued = []

	def queue_switch(self, slot: int, caller=None):
		self.queued.append(slot)


class DummyCaller:
	def __init__(self):
		self.msgs = []
		self.ndb = types.SimpleNamespace()
		self.db = types.SimpleNamespace(battle_control=True)

	def msg(self, text):
		self.msgs.append(text)


def test_battleswitch_prompts_when_no_arg():
	orig_evennia, orig_battle = setup_modules()
	cmd_mod = load_cmd_module()

	poke1 = types.SimpleNamespace(name="Pika", hp=10)
	poke2 = types.SimpleNamespace(name="Bulba", hp=10)
	player = FakeParticipant("Player", [poke1, poke2])
	enemy = FakeParticipant("Enemy", [poke2])
	battle = FakeBattle([player, enemy])
	inst = FakeInstance(battle)
	caller = DummyCaller()
	caller.ndb.battle_instance = inst

	cmd = cmd_mod.CmdBattleSwitch()
	cmd.caller = caller
	cmd.args = ""
	cmd.func()

	joined = "\n".join(caller.msgs)
	assert "Choose a Pokémon" in joined
	assert "Pika" in joined

	cb = caller.ndb.last_prompt_callback
	assert cb is not None
	cb(caller, "", "2")

	restore_modules(orig_evennia, orig_battle)
	assert isinstance(player.pending_action, cmd_mod.Action)
	assert player.pending_action.target is poke2
	assert player.pending_action.priority == 6
	assert inst.ran is False
	assert battle.ran is False


def test_battleswitch_queues_action_and_runs_turn():
	orig_evennia, orig_battle = setup_modules()
	cmd_mod = load_cmd_module()

	poke1 = types.SimpleNamespace(name="Pika", hp=10)
	poke2 = types.SimpleNamespace(name="Bulba", hp=10)
	player = FakeParticipant("Player", [poke1, poke2])
	enemy = FakeParticipant("Enemy", [poke1])
	battle = FakeBattle([player, enemy])
	inst = FakeInstance(battle)
	caller = DummyCaller()
	caller.ndb.battle_instance = inst

	cmd = cmd_mod.CmdBattleSwitch()
	cmd.caller = caller
	cmd.args = "2"
	cmd.func()

	restore_modules(orig_evennia, orig_battle)
	assert isinstance(player.pending_action, cmd_mod.Action)
	assert player.pending_action.target is poke2
	assert player.pending_action.priority == 6
	assert inst.ran is False
	assert battle.ran is False


def test_battleswitch_persists_declare_via_queue_switch():
	orig_evennia, orig_battle = setup_modules()
	cmd_mod = load_cmd_module()

	poke1 = types.SimpleNamespace(name="Pika", hp=10)
	poke2 = types.SimpleNamespace(name="Bulba", hp=10)
	player = FakeParticipant("Player", [poke1, poke2])
	enemy = FakeParticipant("Enemy", [poke1])
	battle = FakeBattle([player, enemy])
	inst = FakeQueueInstance(battle)
	caller = DummyCaller()
	caller.ndb.battle_instance = inst

	cmd = cmd_mod.CmdBattleSwitch()
	cmd.caller = caller
	cmd.args = "2"
	cmd.func()

	restore_modules(orig_evennia, orig_battle)
	assert isinstance(player.pending_action, cmd_mod.Action)
	assert inst.queued == [2]
