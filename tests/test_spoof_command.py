import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")
	fake_evennia.Command = type("Command", (), {})
	sys.modules["evennia"] = fake_evennia

	path = os.path.join(ROOT, "commands", "debug", "command.py")
	spec = importlib.util.spec_from_file_location("commands.debug.command", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)

	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)
	return mod


class DummyRoom:
	def __init__(self, key="Room", location=None):
		self.key = key
		self.location = location
		self.contents = []


class DummyContainer:
	def __init__(self, key="Container", location=None):
		self.key = key
		self.location = location
		self.contents = []


class DummyObject:
	def __init__(self, key, obj_id=None, nospoof=False, location=None, html=False):
		self.key = key
		self.id = obj_id
		self.db = types.SimpleNamespace(nospoof=nospoof, html=html)
		self.location = location
		self.msgs = []

	def msg(self, text):
		self.msgs.append(text)


def test_spoof_emits_raw_to_normal_players_and_attributed_to_nospoof_players():
	mod = load_cmd_module()
	room = DummyRoom()
	caller = DummyObject("TinyJerk", 226, location=room)
	normal = DummyObject("Bystander", 300, location=room)
	nospoof = DummyObject("Wizard", 1, nospoof=True, location=room)
	room.contents = [caller, normal, nospoof]

	cmd = mod.CmdSpoof()
	cmd.caller = caller
	cmd.args = "Wizard is a jerk!"
	cmd.switches = []
	cmd.func()

	assert caller.msgs == ["Wizard is a jerk!"]
	assert normal.msgs == ["Wizard is a jerk!"]
	assert nospoof.msgs == ["[TinyJerk(#226)] Wizard is a jerk!"]


def test_emit_room_switch_targets_outer_room_once():
	mod = load_cmd_module()
	outer = DummyRoom("Outer")
	container = DummyContainer("Container", location=outer)
	caller = DummyObject("TinyJerk", 226, location=container)
	nearby = DummyObject("Nearby", 2, location=container)
	outer_witness = DummyObject("Wizard", 1, nospoof=True, location=outer)
	container.contents = [caller, nearby]
	outer.contents = [outer_witness]

	cmd = mod.CmdSpoof()
	cmd.caller = caller
	cmd.args = "A sound echoes from inside."
	cmd.switches = ["room"]
	cmd.func()

	assert caller.msgs == []
	assert nearby.msgs == []
	assert outer_witness.msgs == ["[TinyJerk(#226)] A sound echoes from inside."]


def test_emit_html_switch_filters_to_html_flagged_recipients():
	mod = load_cmd_module()
	room = DummyRoom()
	caller = DummyObject("TinyJerk", 226, location=room)
	plain = DummyObject("Plain", 2, location=room)
	html = DummyObject("Html", 3, location=room, html=True)
	room.contents = [caller, plain, html]

	cmd = mod.CmdSpoof()
	cmd.caller = caller
	cmd.args = "<b>A styled emit.</b>"
	cmd.switches = ["html"]
	cmd.func()

	assert caller.msgs == []
	assert plain.msgs == []
	assert html.msgs == ["<b>A styled emit.</b>"]


def test_nospoof_toggles_and_accepts_explicit_state():
	mod = load_cmd_module()
	caller = DummyObject("Wizard", 1, nospoof=False)

	cmd = mod.CmdNoSpoof()
	cmd.caller = caller
	cmd.args = ""
	cmd.func()

	assert caller.db.nospoof is True
	assert caller.msgs[-1] == "NOSPOOF is now ON."

	cmd.args = "off"
	cmd.func()

	assert caller.db.nospoof is False
	assert caller.msgs[-1] == "NOSPOOF is now OFF."
