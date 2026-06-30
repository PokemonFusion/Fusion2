import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_cmd_look_module():
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")

	class FakeCommand:
		def msg(self, text=None, options=None, **kwargs):
			self.messages.append((text, options, kwargs))

	fake_evennia.Command = FakeCommand
	sys.modules["evennia"] = fake_evennia

	path = os.path.join(ROOT, "commands", "player", "cmd_look.py")
	spec = importlib.util.spec_from_file_location("commands.player.cmd_look", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	assert spec.loader is not None
	spec.loader.exec_module(mod)

	def restore():
		sys.modules.pop(spec.name, None)
		if orig_evennia is not None:
			sys.modules["evennia"] = orig_evennia
		else:
			sys.modules.pop("evennia", None)

	return mod, restore


class DummyCaller:
	def __init__(self):
		self.key = "Ash"
		self.search_terms = []

	def at_look(self, target):
		return f"LOOK:{target.key}"

	def search(self, term, quiet=False):
		self.search_terms.append((term, quiet))
		return []


def call_look(cmd_mod, caller, args, cmdstring="look"):
	cmd = cmd_mod.CmdLook()
	cmd.caller = caller
	cmd.args = args
	cmd.cmdstring = cmdstring
	cmd.messages = []
	cmd.func()
	return cmd.messages[-1][0]


def test_look_me_resolves_to_caller_without_search():
	cmd_mod, restore = load_cmd_look_module()
	try:
		caller = DummyCaller()
		message = call_look(cmd_mod, caller, "me")

		assert message == ("LOOK:Ash", {"type": "look"})
		assert caller.search_terms == []
	finally:
		restore()


def test_l_me_uses_same_self_shortcut_path():
	cmd_mod, restore = load_cmd_look_module()
	try:
		caller = DummyCaller()
		message = call_look(cmd_mod, caller, "me", cmdstring="l")

		assert "l" in cmd_mod.CmdLook.aliases
		assert message == ("LOOK:Ash", {"type": "look"})
		assert caller.search_terms == []
	finally:
		restore()
