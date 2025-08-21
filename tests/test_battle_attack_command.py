import importlib.util
import os
import sys
import types
from dataclasses import dataclass
from enum import Enum

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
	path = os.path.join(ROOT, "commands", "player", "cmd_battle_attack.py")
	spec = importlib.util.spec_from_file_location("commands.player.cmd_battle_attack", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)
	return mod


class FakeQS(list):
	def all(self):
		return self

	def order_by(self, field):
		return self


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
	orig_battleinstance = sys.modules.get("pokemon.battle.battleinstance")
	orig_engine = sys.modules.get("pokemon.battle.engine")
	orig_ui = sys.modules.get("pokemon.ui")
	orig_ui_move = sys.modules.get("pokemon.ui.move_gui")
	battle_mod = types.ModuleType("pokemon.battle")

	class ActionType(Enum):
		MOVE = 1

	@dataclass
	class Action:
		actor: object
		action_type: ActionType
		target: object = None
		move: object = None
		priority: int = 0

	class BattleMove:
		def __init__(self, name, priority=0, key=None, **kwargs):  # pragma: no cover - stub
			self.name = name
			self.priority = priority
			self.key = key or name

	battle_mod.Action = Action
	battle_mod.ActionType = ActionType
	battle_mod.BattleMove = BattleMove
	sys.modules["pokemon.battle"] = battle_mod

	engine_mod = types.ModuleType("pokemon.battle.engine")
	engine_mod.BattleMove = BattleMove

	def _normalize_key(name: str) -> str:
		return name

	engine_mod._normalize_key = _normalize_key
	sys.modules["pokemon.battle.engine"] = engine_mod

	ui_pkg = types.ModuleType("pokemon.ui")
	ui_move = types.ModuleType("pokemon.ui.move_gui")

	def _render(slots, pp_overrides=None, total_width=76):  # pragma: no cover - stub
		letters = ["A", "B", "C", "D"]
		lines = ["Choose a move:"]
		for idx, s in enumerate(slots[:4]):
			name = s if isinstance(s, str) else getattr(s, "name", "")
			lines.append(f"[{letters[idx]} ] {name}")
		return "\n".join(lines)

	ui_move.render_move_gui = _render
	sys.modules["pokemon.ui"] = ui_pkg
	sys.modules["pokemon.ui.move_gui"] = ui_move

	battleinstance_mod = types.ModuleType("pokemon.battle.battleinstance")

	class BattleSession:
		@staticmethod
		def ensure_for_player(caller):
			return getattr(caller.ndb, "battle_instance", None)

	battleinstance_mod.BattleSession = BattleSession
	sys.modules["pokemon.battle.battleinstance"] = battleinstance_mod

	return orig_evennia, orig_battle, orig_battleinstance, orig_engine, orig_ui, orig_ui_move


def restore_modules(orig_evennia, orig_battle, orig_battleinstance, orig_engine, orig_ui, orig_ui_move):
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
	if orig_battleinstance is not None:
		sys.modules["pokemon.battle.battleinstance"] = orig_battleinstance
	else:
		sys.modules.pop("pokemon.battle.battleinstance", None)
	if orig_engine is not None:
		sys.modules["pokemon.battle.engine"] = orig_engine
	else:
		sys.modules.pop("pokemon.battle.engine", None)
	if orig_ui is not None:
		sys.modules["pokemon.ui"] = orig_ui
	else:
		sys.modules.pop("pokemon.ui", None)
	if orig_ui_move is not None:
		sys.modules["pokemon.ui.move_gui"] = orig_ui_move
	else:
		sys.modules.pop("pokemon.ui.move_gui", None)


class FakeSlot:
	def __init__(self, name, slot):
		self.move = types.SimpleNamespace(name=name)
		self.slot = slot


class FakeParticipant:
	def __init__(self, name, pokemon):
		self.name = name
		self.pokemons = [pokemon]
		self.active = [pokemon]
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


class FakeQueueInstance(FakeInstance):
	def __init__(self, battle):
		super().__init__(battle)
		self.queued = []

	def queue_move(self, move_name, target="B1", caller=None):
		self.queued.append((move_name, target))


class DummyCaller:
	def __init__(self):
		self.msgs = []
		self.ndb = types.SimpleNamespace()
		self.db = types.SimpleNamespace(battle_control=True)

	def msg(self, text):
		self.msgs.append(text)


def test_battleattack_lists_moves_and_targets():
	orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move = setup_modules()
	cmd_mod = load_cmd_module()

	poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot("tackle", 1), FakeSlot("growl", 2)]))
	opp = FakeParticipant("Enemy", poke)
	player = FakeParticipant("Player", poke)
	battle = FakeBattle([player, opp])
	caller = DummyCaller()
	caller.ndb.battle_instance = types.SimpleNamespace(battle=battle)
	caller.db.battle_control = True

	cmd = cmd_mod.CmdBattleAttack()
	cmd.caller = caller
	cmd.args = ""
	cmd.parse()
	cmd.func()
	joined = "\n".join(caller.msgs)
	assert "Choose a move" in joined
	assert "tackle" in joined.lower()

	cb = caller.ndb.last_prompt_callback
	assert cb is not None
	cb(caller, "", "tackle")

	restore_modules(orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move)
	assert isinstance(player.pending_action, cmd_mod.Action)
	assert player.pending_action.target is opp


def test_battleattack_auto_target_single():
	orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move = setup_modules()
	cmd_mod = load_cmd_module()

	poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot("tackle", 1)]))
	player = FakeParticipant("Player", poke)
	enemy = FakeParticipant("Enemy", poke)
	battle = FakeBattle([player, enemy])
	caller = DummyCaller()
	caller.ndb.battle_instance = types.SimpleNamespace(battle=battle)
	caller.db.battle_control = True

	cmd = cmd_mod.CmdBattleAttack()
	cmd.caller = caller
	cmd.args = "tackle"
	cmd.parse()
	cmd.func()

	restore_modules(orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move)
	assert isinstance(player.pending_action, cmd_mod.Action)
	assert player.pending_action.target is enemy


def test_battleattack_prompt_runs_turn_after_callback():
	orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move = setup_modules()
	cmd_mod = load_cmd_module()

	poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot("tackle", 1)]))
	player = FakeParticipant("Player", poke)
	enemy = FakeParticipant("Enemy", poke)
	battle = FakeBattle([player, enemy])
	inst = FakeInstance(battle)
	caller = DummyCaller()
	caller.ndb.battle_instance = inst
	caller.db.battle_control = True

	cmd = cmd_mod.CmdBattleAttack()
	cmd.caller = caller
	cmd.args = ""
	cmd.parse()
	cmd.func()
	assert inst.ran is False
	assert battle.ran is False

	cb = caller.ndb.last_prompt_callback
	assert cb is not None
	cb(caller, "", "tackle")

	restore_modules(orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move)
	assert isinstance(player.pending_action, cmd_mod.Action)
	assert inst.ran is False
	assert battle.ran is False


def test_battleattack_arg_runs_turn():
	orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move = setup_modules()
	cmd_mod = load_cmd_module()

	poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot("tackle", 1)]))
	player = FakeParticipant("Player", poke)
	enemy = FakeParticipant("Enemy", poke)
	battle = FakeBattle([player, enemy])
	inst = FakeInstance(battle)
	caller = DummyCaller()
	caller.ndb.battle_instance = inst
	caller.db.battle_control = True

	cmd = cmd_mod.CmdBattleAttack()
	cmd.caller = caller
	cmd.args = "tackle"
	cmd.parse()
	cmd.func()

	restore_modules(orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move)
	assert isinstance(player.pending_action, cmd_mod.Action)
	assert inst.ran is False
	assert battle.ran is False


def test_battleattack_requires_target_when_multiple():
	orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move = setup_modules()
	cmd_mod = load_cmd_module()

	poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot("tackle", 1)]))
	player = FakeParticipant("Player", poke)
	e1 = FakeParticipant("Foe1", poke)
	e2 = FakeParticipant("Foe2", poke)
	battle = FakeBattle([player, e1, e2])
	caller = DummyCaller()
	caller.ndb.battle_instance = types.SimpleNamespace(battle=battle)
	caller.db.battle_control = True

	cmd = cmd_mod.CmdBattleAttack()
	cmd.caller = caller
	cmd.args = "tackle"
	cmd.parse()
	cmd.func()

	restore_modules(orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move)
	assert player.pending_action is None
	assert "Valid targets" in caller.msgs[-1]
	assert "B1" in caller.msgs[-1]


def test_battleattack_falls_back_to_move_list():
	orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move = setup_modules()
	cmd_mod = load_cmd_module()

	poke = types.SimpleNamespace(moves=[types.SimpleNamespace(name="tackle"), types.SimpleNamespace(name="growl")])
	player = FakeParticipant("Player", poke)
	enemy = FakeParticipant("Enemy", poke)
	battle = FakeBattle([player, enemy])
	caller = DummyCaller()
	caller.ndb.battle_instance = types.SimpleNamespace(battle=battle)
	caller.db.battle_control = True

	cmd = cmd_mod.CmdBattleAttack()
	cmd.caller = caller
	cmd.args = ""
	cmd.parse()
	cmd.func()
	msg = "\n".join(caller.msgs)
	assert "tackle" in msg.lower()
	assert "[A ]" in msg

	cb = caller.ndb.last_prompt_callback
	assert cb is not None
	cb(caller, "", "A")

	restore_modules(orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move)
	assert isinstance(player.pending_action, cmd_mod.Action)
	assert player.pending_action.target is enemy


def test_battleattack_uses_caller_participant():
	orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move = setup_modules()
	cmd_mod = load_cmd_module()

	poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot("tackle", 1)]))
	caller1 = DummyCaller()
	caller2 = DummyCaller()

	p1 = FakeParticipant("P1", poke)
	p1.player = caller1
	p2 = FakeParticipant("P2", poke)
	p2.player = caller2
	battle = FakeBattle([p1, p2])

	caller2.ndb.battle_instance = types.SimpleNamespace(battle=battle)
	caller2.db.battle_control = True

	cmd = cmd_mod.CmdBattleAttack()
	cmd.caller = caller2
	cmd.args = "tackle"
	cmd.parse()
	cmd.func()

	restore_modules(orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move)
	assert isinstance(p2.pending_action, cmd_mod.Action)
	assert p1.pending_action is None


def test_battleattack_persists_declare_via_queue_move():
	orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move = setup_modules()
	cmd_mod = load_cmd_module()

	poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot("tackle", 1)]))
	player = FakeParticipant("Player", poke)
	enemy = FakeParticipant("Enemy", poke)
	battle = FakeBattle([player, enemy])
	inst = FakeQueueInstance(battle)
	caller = DummyCaller()
	caller.ndb.battle_instance = inst
	caller.db.battle_control = True

	cmd = cmd_mod.CmdBattleAttack()
	cmd.caller = caller
	cmd.args = "tackle"
	cmd.parse()
	cmd.func()

	restore_modules(orig_evennia, orig_battle, orig_bi, orig_engine, orig_ui, orig_ui_move)
	assert isinstance(player.pending_action, cmd_mod.Action)
	assert inst.queued == [("tackle", "B1")]
