import importlib.util
import os
import sys
import types
from dataclasses import dataclass
from enum import Enum

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
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
		pokemon: object = None

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
	assert player.pending_action.pokemon is poke2
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
	assert player.pending_action.pokemon is poke2
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
	assert player.pending_action.pokemon is poke2
	assert inst.queued == [2]


@pytest.mark.parametrize("prompted", [False, True])
def test_battleswitch_keeps_party_slots_with_gaps_and_reordered_roster(prompted):
	"""A canonical slot maps by owned identity, never by the compact roster index."""
	originals = setup_modules()
	try:
		cmd_mod = load_cmd_module()
		second = types.SimpleNamespace(name="Second", hp=10, model_id="owned:second")
		sixth = types.SimpleNamespace(name="Sixth", hp=10, model_id="owned:sixth")
		player = FakeParticipant("Player", [sixth, second])
		player.active = [second]
		inst = FakeQueueInstance(FakeBattle([player]))
		caller = DummyCaller()
		caller.storage = types.SimpleNamespace(get_party_slots=lambda: [None, types.SimpleNamespace(unique_id="second"),
			None, None, None, types.SimpleNamespace(unique_id="sixth")])
		caller.ndb.battle_instance = inst
		cmd = cmd_mod.CmdBattleSwitch()
		cmd.caller, cmd.args = caller, "" if prompted else "6"
		cmd.func()
		if prompted:
			assert "2. Second" in caller.msgs[-1]
			assert "6. Sixth" in caller.msgs[-1]
			assert "1. Sixth" not in caller.msgs[-1]
			caller.ndb.last_prompt_callback(caller, "", "6")
		assert player.pending_action.pokemon is sixth
		assert inst.queued == [1]
	finally:
		restore_modules(*originals)


@pytest.mark.parametrize("selection", ["1", "3", "-1", "7"])
def test_battleswitch_rejects_empty_or_out_of_range_party_slot(selection):
	"""Invalid slots cannot select a roster member through Python indexing."""
	originals = setup_modules()
	try:
		cmd_mod = load_cmd_module()
		mon = types.SimpleNamespace(name="Sixth", hp=10, model_id="owned:sixth")
		player = FakeParticipant("Player", [mon])
		inst = FakeQueueInstance(FakeBattle([player]))
		caller = DummyCaller()
		caller.storage = types.SimpleNamespace(get_party_slots=lambda: [None] * 5 + [types.SimpleNamespace(unique_id="sixth")])
		caller.ndb.battle_instance = inst
		cmd = cmd_mod.CmdBattleSwitch()
		cmd.caller, cmd.args = caller, selection
		cmd.func()
		assert "Invalid Pokémon slot" in caller.msgs[-1]
		assert inst.queued == []
		assert player.pending_action is None
	finally:
		restore_modules(*originals)


def test_battleswitch_reserved_fusion_matches_the_party_sheet_display_slot():
	"""A reserved Fusion may use a free display slot without shifting real members."""
	originals = setup_modules()
	try:
		cmd_mod = load_cmd_module()
		fusion = types.SimpleNamespace(name="Fusion", model_id="owned:form", hp=10)
		second = types.SimpleNamespace(name="Second", model_id="owned:second", hp=10)
		participant = FakeParticipant("Player", [second, fusion])
		caller = DummyCaller()
		caller.db.fusion_id = "form"
		caller.storage = types.SimpleNamespace(get_party_slots=lambda: [None, types.SimpleNamespace(unique_id="second")] + [None] * 4)
		command = cmd_mod.CmdBattleSwitch()
		command.caller = caller
		assert command._choices(participant) == {1: (2, fusion), 2: (1, second)}
	finally:
		restore_modules(*originals)


@pytest.mark.parametrize("order", ["normal", "first"])
@pytest.mark.parametrize("prompted", [False, True])
def test_battleswitch_full_party_fusion_remains_selectable(order, prompted):
	"""The seventh roster member has a named choice without renumbering party slots."""
	originals = setup_modules()
	try:
		cmd_mod = load_cmd_module()
		mons = [types.SimpleNamespace(name=f"Party {i}", model_id=f"owned:{i}", hp=10) for i in range(1, 7)]
		fusion = types.SimpleNamespace(name="Fusion", model_id="owned:form", hp=10)
		roster = [fusion, *mons] if order == "first" else [*mons, fusion]
		participant = FakeParticipant("Player", roster)
		participant.active = [mons[0]]
		instance = FakeQueueInstance(FakeBattle([participant]))
		caller = DummyCaller()
		caller.storage = types.SimpleNamespace(get_party_slots=lambda: [types.SimpleNamespace(unique_id=str(i)) for i in range(1, 7)])
		caller.db.fusion_id = "form"
		caller.ndb.battle_instance = instance
		command = cmd_mod.CmdBattleSwitch()
		command.caller, command.args = caller, "" if prompted else "fusion"
		command.func()
		if prompted:
			assert "fusion. Fusion" in caller.msgs[-1]
			assert "6. Party 6" in caller.msgs[-1]
			caller.ndb.last_prompt_callback(caller, "", "Fusion")
		assert participant.pending_action.pokemon is fusion
		assert instance.queued == [1 if order == "first" else 7]
		participant.active = [fusion]
		command.args = "6"
		command.func()
		assert participant.pending_action.pokemon is mons[5]
		assert instance.queued[-1] == (7 if order == "first" else 6)
		participant.active = [mons[5]]
		command.args = "fusion"
		command.func()
		assert participant.pending_action.pokemon is fusion
	finally:
		restore_modules(*originals)
